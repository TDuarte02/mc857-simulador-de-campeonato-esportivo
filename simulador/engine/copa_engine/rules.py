"""
Regras do campeonato que não dependem de estado: sementes derivadas, sorteio
dos grupos por potes, tabela de jogos dos grupos, classificação com critérios
de desempate e chaveamento do mata-mata.

Quem orquestra o campeonato (e guarda o estado) é o servidor; este módulo só
decide, de forma determinística a partir da semente.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

# ============================================================
# Sementes
# ============================================================

def derive_seed(tournament_seed: int, *labels: object) -> int:
    """
    Semente derivada e estável: SHA-256 de (semente, rótulos), 64 bits.

    Idêntica entre execuções e processos (não usa `hash()` nem contadores).
    """
    if isinstance(tournament_seed, bool) or not isinstance(tournament_seed, int):
        raise ValueError(f"A semente do torneio deve ser um inteiro; recebido: {tournament_seed!r}")
    payload = json.dumps(
        [tournament_seed, *(str(label) for label in labels)],
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:8], "big")


# ============================================================
# Potes e sorteio
# ============================================================

GROUP_NAMES: tuple[str, ...] = ("A", "B", "C", "D")
TEAMS_PER_GROUP = 4
N_TEAMS = len(GROUP_NAMES) * TEAMS_PER_GROUP  # 16
N_POTS = TEAMS_PER_GROUP


class Entrant(Protocol):
    """O que o sorteio precisa de uma seleção: nome único e força."""

    @property
    def name(self) -> str: ...

    @property
    def strength(self) -> float: ...


@dataclass(frozen=True)
class Group:
    name: str
    teams: tuple[Entrant, ...]  # índice + 1 = posição no grupo = nº do pote

    def position_of(self, team_name: str) -> int:
        for index, team in enumerate(self.teams, start=1):
            if team.name == team_name:
                return index
        raise ValueError(f"{team_name!r} não está no grupo {self.name}.")


@dataclass(frozen=True)
class DrawResult:
    pots: tuple[tuple[Entrant, ...], ...]
    groups: tuple[Group, ...]


def draw_groups(teams: Sequence[Entrant], seed: int) -> DrawResult:
    """
    Ordena por força (desempate por nome), divide em 4 potes de 4 e sorteia
    os grupos A-D: cada grupo recebe um time de cada pote. A posição no
    grupo é o número do pote. O pote p usa Random(derive_seed(seed, "draw", p)).
    """
    if len(teams) != N_TEAMS:
        raise ValueError(f"O sorteio exige {N_TEAMS} seleções; recebido: {len(teams)}")
    if len({t.name for t in teams}) != N_TEAMS:
        raise ValueError("Os nomes das seleções devem ser únicos.")

    ranked = sorted(teams, key=lambda t: (-t.strength, t.name))
    pots = tuple(
        tuple(ranked[p * TEAMS_PER_GROUP:(p + 1) * TEAMS_PER_GROUP]) for p in range(N_POTS)
    )

    members: list[list[Entrant]] = [[] for _ in GROUP_NAMES]
    for pot_number, pot in enumerate(pots, start=1):
        order = list(pot)
        random.Random(derive_seed(seed, "draw", pot_number)).shuffle(order)
        for group_index, team in enumerate(order):
            members[group_index].append(team)

    groups = tuple(Group(name, tuple(ts)) for name, ts in zip(GROUP_NAMES, members))
    return DrawResult(pots, groups)


# ============================================================
# Tabela de jogos
# ============================================================

# Posições no grupo (1 a 4, definidas pelo pote).
GROUP_ROUNDS: tuple[tuple[tuple[int, int], ...], ...] = (
    ((1, 2), (3, 4)),
    ((1, 3), (2, 4)),
    ((1, 4), (2, 3)),
)


# ============================================================
# Classificação
# ============================================================

WIN_POINTS = 3
DRAW_POINTS = 1


@dataclass(frozen=True)
class GroupGame:
    team_a: str
    team_b: str
    goals_a: int
    goals_b: int


@dataclass(frozen=True)
class StandingRow:
    team: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    points: int

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against


def _points(goals_for: int, goals_against: int) -> int:
    if goals_for > goals_against:
        return WIN_POINTS
    return DRAW_POINTS if goals_for == goals_against else 0


def _break_tie(tied: list[str], games: Sequence[GroupGame], rng: random.Random) -> list[str]:
    """
    Critérios 4 a 6 (confronto direto, só jogos entre os empatados) e, se
    nada separar ninguém, o sorteio (critério 7). Se o empate se desfaz
    parcialmente, reaplica 4 a 6 ao subconjunto que continua empatado.
    """
    if len(tied) == 1:
        return tied

    members = set(tied)
    stats = {t: [0, 0, 0] for t in tied}   # pontos, gols pró, gols contra
    for g in games:
        if g.team_a in members and g.team_b in members:
            for team, gf, ga in ((g.team_a, g.goals_a, g.goals_b), (g.team_b, g.goals_b, g.goals_a)):
                stats[team][0] += _points(gf, ga)
                stats[team][1] += gf
                stats[team][2] += ga

    buckets: dict[tuple[int, int, int], list[str]] = {}
    for team in tied:
        pts, gf, ga = stats[team]
        buckets.setdefault((pts, gf - ga, gf), []).append(team)

    if len(buckets) == 1:                       # nada separou: sorteio
        order = sorted(tied)
        rng.shuffle(order)
        return order

    ordered: list[str] = []
    for key in sorted(buckets, reverse=True):
        ordered += _break_tie(buckets[key], games, rng)
    return ordered


def compute_standings(
    group_name: str,
    team_names: Sequence[str],
    games: Sequence[GroupGame],
    seed: int,
) -> tuple[StandingRow, ...]:
    """
    Classificação de um grupo a partir dos jogos encerrados.

    Critérios: 1) pontos; 2) saldo; 3) gols marcados; 4-6) pontos, saldo e
    gols no confronto direto; 7) sorteio com Random(derive_seed(seed,
    "tiebreak", grupo)).
    """
    names = set(team_names)
    acc = {t: dict(w=0, d=0, l=0, gf=0, ga=0) for t in team_names}
    for g in games:
        if g.team_a not in names or g.team_b not in names or g.team_a == g.team_b:
            raise ValueError(f"Jogo fora do grupo {group_name}: {g.team_a} x {g.team_b}")
        for team, gf, ga in ((g.team_a, g.goals_a, g.goals_b), (g.team_b, g.goals_b, g.goals_a)):
            a = acc[team]
            a["gf"] += gf
            a["ga"] += ga
            a["w" if gf > ga else "d" if gf == ga else "l"] += 1

    rows = {
        t: StandingRow(
            team=t,
            played=a["w"] + a["d"] + a["l"],
            wins=a["w"], draws=a["d"], losses=a["l"],
            goals_for=a["gf"], goals_against=a["ga"],
            points=WIN_POINTS * a["w"] + DRAW_POINTS * a["d"],
        )
        for t, a in acc.items()
    }

    rng = random.Random(derive_seed(seed, "tiebreak", group_name))
    by_key: dict[tuple[int, int, int], list[str]] = {}
    for t in sorted(rows):
        r = rows[t]
        by_key.setdefault((r.points, r.goal_diff, r.goals_for), []).append(t)

    order: list[str] = []
    for key in sorted(by_key, reverse=True):
        order += _break_tie(by_key[key], games, rng)
    return tuple(rows[t] for t in order)


# ============================================================
# Chaves do mata-mata
# ============================================================

@dataclass(frozen=True)
class SlotSource:
    """Origem de uma vaga: posição em um grupo, ou vencedor/perdedor de uma partida."""

    kind: str          # "group" | "winner" | "loser"
    ref: str           # nome do grupo ou id da partida
    position: int = 0  # só para "group"

    @property
    def label(self) -> str:
        if self.kind == "group":
            return f"{self.position}º {self.ref}"
        if self.kind == "winner":
            return f"Vencedor {self.ref}"
        return f"Perdedor {self.ref}"


def _group(name: str, position: int) -> SlotSource:
    return SlotSource("group", name, position)


def _winner(match_id: str) -> SlotSource:
    return SlotSource("winner", match_id)


def _loser(match_id: str) -> SlotSource:
    return SlotSource("loser", match_id)


KNOCKOUT_BRACKET: dict[str, tuple[SlotSource, SlotSource]] = {
    "QF1": (_group("A", 1), _group("B", 2)),
    "QF2": (_group("B", 1), _group("A", 2)),
    "QF3": (_group("D", 1), _group("C", 2)),
    "QF4": (_group("C", 1), _group("D", 2)),
    "SF1": (_winner("QF1"), _winner("QF2")),
    "SF2": (_winner("QF3"), _winner("QF4")),
    "THIRD": (_loser("SF1"), _loser("SF2")),
    "FINAL": (_winner("SF1"), _winner("SF2")),
}
# Ordem de jogo: cada partida só depende das anteriores.
KNOCKOUT_ORDER: tuple[str, ...] = tuple(KNOCKOUT_BRACKET)
