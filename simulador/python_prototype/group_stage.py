"""
Fase de grupos (Issue #34): estado do torneio, tabela de jogos, simulação de
partidas máquina x máquina e classificação com critérios de desempate.
"""
from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum

from python_prototype.match import MatchEvent, create_match, play_match
from python_prototype.tournament import (
    Group,
    NationalTeam,
    TournamentSetup,
    derive_seed,
)

# ============================================================
# Estruturas
# ============================================================

class TournamentPhase(str, Enum):
    SORTEIO = "SORTEIO"
    GRUPOS = "GRUPOS"
    MATA_MATA = "MATA_MATA"
    ENCERRADO = "ENCERRADO"


class MatchStatus(str, Enum):
    PENDENTE = "PENDENTE"
    ENCERRADA = "ENCERRADA"


@dataclass(frozen=True)
class MatchResult:
    """Placar dos 90 minutos e log de eventos da partida."""

    goals_a: int
    goals_b: int
    events: tuple[MatchEvent, ...]


@dataclass
class MatchRecord:
    match_id: str
    phase: TournamentPhase
    team_a: str
    team_b: str
    status: MatchStatus = MatchStatus.PENDENTE
    result: MatchResult | None = None
    group: str | None = None
    round_number: int | None = None


@dataclass
class TournamentState:
    config: "TournamentConfig"  # noqa: F821  (definido em tournament.py)
    teams: dict[str, NationalTeam]
    groups: tuple[Group, ...]
    phase: TournamentPhase = TournamentPhase.GRUPOS
    matches: dict[str, MatchRecord] = field(default_factory=dict)

    @classmethod
    def from_setup(cls, setup: TournamentSetup) -> "TournamentState":
        """Estado após o sorteio: fase de grupos com a tabela de jogos gerada."""
        state = cls(
            config=setup.config,
            teams={t.name: t for t in setup.teams},
            groups=setup.draw.groups,
        )
        for record in build_group_schedule(state.groups):
            state.matches[record.match_id] = record
        return state

    def match(self, match_id: str) -> MatchRecord:
        try:
            return self.matches[match_id]
        except KeyError:
            raise ValueError(f"Partida desconhecida: {match_id!r}") from None

    def group(self, name: str) -> Group:
        for group in self.groups:
            if group.name == name:
                return group
        raise ValueError(f"Grupo desconhecido: {name!r}")

    def group_matches(self, name: str) -> list[MatchRecord]:
        return [m for m in self.matches.values() if m.phase is TournamentPhase.GRUPOS and m.group == name]

    @property
    def group_stage_finished(self) -> bool:
        return all(
            m.status is MatchStatus.ENCERRADA
            for m in self.matches.values()
            if m.phase is TournamentPhase.GRUPOS
        )


# ============================================================
# Tabela de jogos
# ============================================================

# Posições no grupo (1 a 4, definidas pelo pote).
GROUP_ROUNDS: tuple[tuple[tuple[int, int], ...], ...] = (
    ((1, 2), (3, 4)),
    ((1, 3), (2, 4)),
    ((1, 4), (2, 3)),
)


def build_group_schedule(groups: Sequence[Group]) -> list[MatchRecord]:
    """24 partidas (4 grupos x 3 rodadas x 2), com ids como `G-A-R1-1`."""
    records = []
    for group in groups:
        for round_number, pairs in enumerate(GROUP_ROUNDS, start=1):
            for index, (pa, pb) in enumerate(pairs, start=1):
                records.append(
                    MatchRecord(
                        match_id=f"G-{group.name}-R{round_number}-{index}",
                        phase=TournamentPhase.GRUPOS,
                        team_a=group.teams[pa - 1].name,
                        team_b=group.teams[pb - 1].name,
                        group=group.name,
                        round_number=round_number,
                    )
                )
    return records


# ============================================================
# Simulação de partida de máquina
# ============================================================

def simulate_machine_match(
    state: TournamentState, team_a: str, team_b: str, match_id: str
) -> MatchResult:
    """
    Simula uma partida sem alterar o estado do torneio.

    Semente da partida: derive_seed(seed, match_id); da dinâmica (Issue #15):
    derive_seed(seed, match_id, "dynamics"). O resultado só depende dos dois
    times, das escalações e da configuração, nunca da ordem das demais partidas.
    """
    config = state.config
    a, b = state.teams[team_a], state.teams[team_b]
    match = create_match(a.lineup, a.formation, b.lineup, b.formation)
    play_match(
        match,
        seed=derive_seed(config.seed, match_id),
        attack_params=config.attack_params,
        recovery_control_bonus=config.recovery_control_bonus,
        possessions_per_cycle=config.possessions_per_cycle,
        dynamics=config.dynamics,
        dynamics_seed=derive_seed(config.seed, match_id, "dynamics"),
    )
    return MatchResult(match.score["A"], match.score["B"], tuple(match.events))


def play_machine_match(state: TournamentState, match_id: str) -> MatchRecord:
    """Joga uma partida pendente de máquina. Rejeita repetição sem alterar o estado."""
    record = state.match(match_id)
    if record.status is MatchStatus.ENCERRADA:
        raise ValueError(f"A partida {match_id} já foi jogada.")
    if record.phase is not state.phase:
        raise ValueError(
            f"A partida {match_id} é da fase {record.phase.value}, "
            f"mas o torneio está em {state.phase.value}."
        )

    result = simulate_machine_match(state, record.team_a, record.team_b, match_id)

    record.result = result       # commit só depois da simulação completa
    record.status = MatchStatus.ENCERRADA
    return record


def simulate_group_stage(state: TournamentState) -> dict[str, "GroupStandings"]:
    """Joga, só por máquina, as partidas de grupo ainda pendentes (em ordem da tabela)."""
    if state.phase is not TournamentPhase.GRUPOS:
        raise ValueError("O torneio não está na fase de grupos.")
    for record in list(state.matches.values()):
        if record.phase is TournamentPhase.GRUPOS and record.status is MatchStatus.PENDENTE:
            play_machine_match(state, record.match_id)
    return {g.name: group_standings(state, g.name) for g in state.groups}


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


@dataclass(frozen=True)
class GroupStandings:
    group: str
    rows: tuple[StandingRow, ...]   # em ordem de classificação
    is_final: bool                  # só é final após as 6 partidas


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


def group_standings(state: TournamentState, group_name: str) -> GroupStandings:
    """Classificação atual do grupo; `is_final` só vale após as 6 partidas."""
    group = state.group(group_name)
    finished = [
        m for m in state.group_matches(group_name)
        if m.status is MatchStatus.ENCERRADA and m.result is not None
    ]
    games = [
        GroupGame(m.team_a, m.team_b, m.result.goals_a, m.result.goals_b) for m in finished
    ]
    rows = compute_standings(
        group_name, [t.name for t in group.teams], games, state.config.seed
    )
    return GroupStandings(group_name, rows, is_final=len(finished) == 6)
