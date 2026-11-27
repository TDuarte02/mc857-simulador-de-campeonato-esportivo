"""
Dados derivados do log de eventos (Issue #41): autor e minuto de exibição de
cada gol, cartões e duração das lesões.

Funções puras, calculadas DEPOIS da partida: não alteram estado nem usam o
RNG da partida. Cada sorteio tem gerador próprio, derivado da semente do
torneio e do id da partida:

- autores dos gols: Random(derive_seed(seed, match_id, "scorers"));
- cartões: derive_seed(seed, match_id, "cards");
- lesões: Random(derive_seed(seed, match_id, "injury", player_id)).
"""
from __future__ import annotations

import random
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from copa_engine.cards import DEFAULT_CARD_CONFIG, CardConfig, derive_cards
from copa_engine.collective_attributes import (
    POSITION_WEIGHTS,
    Player,
    calculate_player_scores,
    canonical_position,
)
from copa_engine.common import TeamId
from copa_engine.match import CYCLE_MINUTES, HALFTIME_MINUTE, MatchEvent, MatchEventType
from copa_engine.rules import derive_seed

T = MatchEventType

# Uma lesão tira o jogador de 1 a INJURY_MAX_MATCHES partidas.
INJURY_MAX_MATCHES = 3


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


def pick_scorer(players: Sequence[Player], rng: random.Random) -> Player:
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


@dataclass(frozen=True)
class GoalDetail:
    """Gol do log com minuto de exibição e autor."""

    minute: int        # minuto de exibição, dentro do ciclo
    team: TeamId
    player: Player
    event_index: int   # índice do GOAL no log


def derive_goals(
    events: Sequence[MatchEvent], lineups: MatchLineups, *, seed: int, match_id: str
) -> tuple[GoalDetail, ...]:
    """Um autor por gol, sorteado entre os jogadores de linha em campo, na ordem do log."""
    possessions = Counter(e.minute for e in events if e.type is T.MD3_RESULT)
    scorer_rng = random.Random(derive_seed(seed, match_id, "scorers"))
    seen: Counter[int] = Counter()
    goals: list[GoalDetail] = []
    for index, ev in enumerate(events):
        if ev.type is T.MD3_RESULT:
            seen[ev.minute] += 1
        elif ev.type is T.GOAL:
            minute = display_minute(ev.minute, seen[ev.minute], possessions[ev.minute])
            shooter = pick_scorer(lineups.at(ev.team, ev.minute), scorer_rng)
            goals.append(GoalDetail(minute, ev.team, shooter, index))
    return tuple(goals)


def foul_minute(events: Sequence[MatchEvent], foul_index: int) -> int:
    """Minuto de exibição da FALTA no índice `foul_index` do log."""
    foul = events[foul_index]
    possessions = sum(1 for e in events if e.type is T.MD3_RESULT and e.minute == foul.minute)
    return display_minute(foul.minute, foul.data["possession"], possessions)


def derive_match_cards(
    events: Sequence[MatchEvent],
    lineups: MatchLineups,
    config: CardConfig = DEFAULT_CARD_CONFIG,
    *,
    seed: int,
    match_id: str,
) -> tuple[MatchEvent, ...]:
    """`derive_cards` com a semente da partida: derive_seed(seed, match_id, "cards")."""
    return derive_cards(
        events, lineups.at, config, seed=derive_seed(seed, match_id, "cards")
    )


def injury_matches(seed: int, match_id: str, player_id: object) -> int:
    """Partidas que um lesionado perde: 1 + Random(derive_seed(seed, match_id, "injury", id)).randrange(3)."""
    rng = random.Random(derive_seed(seed, match_id, "injury", player_id))
    return 1 + rng.randrange(INJURY_MAX_MATCHES)
