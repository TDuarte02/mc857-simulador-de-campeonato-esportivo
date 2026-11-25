"""
Dados derivados do log de eventos (Issue #41): estatísticas e linha do tempo
de uma partida. Função pura: não altera estado nem usa o RNG da partida.
"""
from __future__ import annotations

import random
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from python_prototype.collective_attributes import (
    POSITION_WEIGHTS,
    Player,
    calculate_player_scores,
    canonical_position,
)
from python_prototype.common import TEAM_IDS, TeamId
from python_prototype.match import CYCLE_MINUTES, HALFTIME_MINUTE, MatchEvent, MatchEventType
from python_prototype.penalties import PenaltyShootout
from python_prototype.tournament import derive_seed

T = MatchEventType


@dataclass(frozen=True)
class MatchLineups:
    """Jogadores em campo no 1º e no 2º tempo (a escalação só muda no intervalo)."""

    first_half: Mapping[TeamId, Sequence[Player]]
    second_half: Mapping[TeamId, Sequence[Player]]

    @classmethod
    def constant(cls, a: Sequence[Player], b: Sequence[Player]) -> "MatchLineups":
        both = {"A": tuple(a), "B": tuple(b)}
        return cls(both, both)

    def at(self, team: TeamId, minute: int) -> Sequence[Player]:
        return (self.first_half if minute < HALFTIME_MINUTE else self.second_half)[team]


def display_minute(start: int, j: int, k: int) -> int:
    """Posse `j` de `k` no ciclo que começa em `start`: start + floor(15 * j / (k + 1))."""
    return start + (CYCLE_MINUTES * j) // (k + 1)


def _pick_scorer(players: Sequence[Player], rng: random.Random) -> Player:
    """Um sorteio por gol, ponderado por peso posicional de ataque x pontuação de ataque."""
    outfield = [p for p in players if canonical_position(p.pos) != "GK"]
    weights = [
        POSITION_WEIGHTS[canonical_position(p.pos)]["attack"] * calculate_player_scores(p).attack
        for p in outfield
    ]
    u = rng.random()
    total = sum(weights)
    if total <= 0:
        return outfield[int(u * len(outfield))]
    target, acc = u * total, 0.0
    for player, weight in zip(outfield, weights):
        acc += weight
        if target < acc:
            return player
    return outfield[-1]


def _entry(minute, type_, team=None, player=None, score=None, data=None) -> dict[str, Any]:
    return {
        "minute": minute, "type": type_, "team": team, "player": player,
        "score": score, "data": data or {},
    }


def build_match_view(
    *,
    match_id: str,
    seed: int,
    team_names: Mapping[TeamId, str],
    events: Sequence[MatchEvent],
    card_events: Sequence[MatchEvent],
    lineups: MatchLineups,
    penalties: PenaltyShootout | None = None,
) -> dict[str, Any]:
    """
    Estatísticas e linha do tempo. LESAO e FALTA isolada não aparecem na linha
    do tempo (faltas só entram na contagem); chutes e xG não existem.
    """
    cards_by_foul: dict[int, list[MatchEvent]] = defaultdict(list)
    for card in card_events:
        cards_by_foul[card.data["foul_event"]].append(card)

    possessions = Counter(e.minute for e in events if e.type is T.MD3_RESULT)
    scorer_rng = random.Random(derive_seed(seed, match_id, "scorers"))
    score = {"A": 0, "B": 0}
    raw = {
        t: Counter() for t in TEAM_IDS
    }
    seen: Counter[int] = Counter()
    rows: list[tuple[int, int, int, dict[str, Any]]] = []

    for index, ev in enumerate(events):
        if ev.type is T.MD3_RESULT:
            seen[ev.minute] += 1
            raw[ev.team]["md3"] += 1
        elif ev.type is T.ATTACK_SEQUENCE:
            raw[ev.team]["attacks"] += 1
            raw[ev.team]["attempts"] += ev.data["attempts"]
        elif ev.type is T.POSSESSION_LOST:
            raw[ev.team]["possession_lost"] += 1
        elif ev.type is T.GOAL:
            minute = display_minute(ev.minute, seen[ev.minute], possessions[ev.minute])
            score[ev.team] += 1
            shooter = _pick_scorer(lineups.at(ev.team, ev.minute), scorer_rng)
            rows.append((minute, index, 0, _entry(minute, "GOAL", ev.team, shooter.name, dict(score))))
        elif ev.type is T.FALTA:
            raw[ev.team]["fouls"] += 1
            minute = display_minute(ev.minute, ev.data["possession"], possessions[ev.minute])
            for sub, card in enumerate(cards_by_foul.get(index, ()), start=1):
                key = "red_cards" if card.type is T.CARTAO_VERMELHO else "yellow_cards"
                raw[card.team][key] += 1
                rows.append((minute, index, sub, _entry(
                    minute, card.type.value, card.team, card.data["player"])))
        elif ev.type in (T.HALFTIME, T.FULL_TIME):
            rows.append((ev.minute, index, 0, _entry(ev.minute, ev.type.value, score=dict(score))))
        elif ev.type is T.LINEUP_CHANGE:
            rows.append((ev.minute, index, 0, _entry(ev.minute, ev.type.value, ev.team)))

    penalties_out = None
    if penalties is not None:
        penalties_out = {
            "first_team": penalties.first_team,
            "goals_a": penalties.goals_a,
            "goals_b": penalties.goals_b,
            "winner": penalties.winner,
            "sudden_death": penalties.sudden_death,
            "kicks": [
                {"team": k.team, "player": k.player, "scored": k.scored} for k in penalties.kicks
            ],
        }
        rows.append((events[-1].minute if events else 90, len(events), 0, _entry(
            events[-1].minute if events else 90, "PENALTIS", penalties.winner,
            score={"A": penalties.goals_a, "B": penalties.goals_b},
            data={"first_team": penalties.first_team, "sudden_death": penalties.sudden_death},
        )))

    total_md3 = sum(raw[t]["md3"] for t in TEAM_IDS)
    stats = {
        t: {
            "goals": score[t],
            "possession": round(100.0 * raw[t]["md3"] / total_md3, 1) if total_md3 else 0.0,
            "attacks": raw[t]["attacks"],
            "attempts": raw[t]["attempts"],
            "possession_lost": raw[t]["possession_lost"],
            "fouls": raw[t]["fouls"],
            "yellow_cards": raw[t]["yellow_cards"],
            "red_cards": raw[t]["red_cards"],
        }
        for t in TEAM_IDS
    }
    rows.sort(key=lambda r: r[:3])
    return {
        "match_id": match_id,
        "team_a": team_names["A"],
        "team_b": team_names["B"],
        "score": dict(score),
        "penalties": penalties_out,
        "stats": stats,
        "timeline": [r[3] for r in rows],
    }
