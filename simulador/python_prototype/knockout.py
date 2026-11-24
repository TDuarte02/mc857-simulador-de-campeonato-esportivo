"""
Mata-mata (Issue #35): chaves com vagas, simulação de partidas de máquina com
pênaltis para empates nos 90 minutos e fechamento do torneio.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from python_prototype.group_stage import (
    MatchRecord,
    MatchResult,
    MatchStatus,
    TournamentPhase,
    TournamentState,
    group_standings,
    simulate_machine_match_state,
)
from python_prototype.penalties import simulate_penalty_shootout
from python_prototype.tournament import derive_seed


# ============================================================
# Chaves
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


def build_knockout_schedule() -> list[MatchRecord]:
    """As 8 partidas do mata-mata, com vagas descritas e ainda indefinidas."""
    return [
        MatchRecord(
            match_id=match_id,
            phase=TournamentPhase.MATA_MATA,
            team_a=None,
            team_b=None,
            slot_a=source_a.label,
            slot_b=source_b.label,
        )
        for match_id, (source_a, source_b) in KNOCKOUT_BRACKET.items()
    ]


# ============================================================
# Vencedor / perdedor
# ============================================================

def _finished_result(record: MatchRecord) -> MatchResult:
    if record.status is not MatchStatus.ENCERRADA or record.result is None:
        raise ValueError(f"A partida {record.match_id} ainda não foi jogada.")
    return record.result


def match_winner(record: MatchRecord) -> str:
    """Vencedor nos 90 minutos ou, em caso de empate, nos pênaltis."""
    result = _finished_result(record)
    if result.goals_a != result.goals_b:
        return record.team_a if result.goals_a > result.goals_b else record.team_b
    if result.penalties is None:
        raise ValueError(f"A partida {record.match_id} terminou empatada, sem pênaltis.")
    return record.team_a if result.penalties.winner == "A" else record.team_b


def match_loser(record: MatchRecord) -> str:
    winner = match_winner(record)
    return record.team_b if winner == record.team_a else record.team_a


# ============================================================
# Preenchimento das vagas
# ============================================================

def _resolve(state: TournamentState, source: SlotSource) -> str | None:
    if source.kind == "group":
        standings = group_standings(state, source.ref)
        return standings.rows[source.position - 1].team if standings.is_final else None
    record = state.matches.get(source.ref)
    if record is None or record.status is not MatchStatus.ENCERRADA:
        return None
    return match_winner(record) if source.kind == "winner" else match_loser(record)


def update_knockout_slots(state: TournamentState) -> None:
    """
    Cria as partidas do mata-mata (se ainda não existirem) e preenche as vagas
    cuja origem terminou: grupo concluído ou partida encerrada. Vagas já
    preenchidas nunca mudam. Pode ser chamada a qualquer momento.
    """
    for record in build_knockout_schedule():
        state.matches.setdefault(record.match_id, record)

    for match_id, (source_a, source_b) in KNOCKOUT_BRACKET.items():
        record = state.matches[match_id]
        if record.status is MatchStatus.ENCERRADA:
            continue
        if record.team_a is None:
            record.team_a = _resolve(state, source_a)
        if record.team_b is None:
            record.team_b = _resolve(state, source_b)


def start_knockout(state: TournamentState) -> None:
    """Encerra a fase de grupos: cria as chaves e passa o torneio para o mata-mata."""
    if state.phase is not TournamentPhase.GRUPOS:
        raise ValueError("O torneio não está na fase de grupos.")
    if not state.group_stage_finished:
        raise ValueError("A fase de grupos ainda não terminou.")
    update_knockout_slots(state)
    state.phase = TournamentPhase.MATA_MATA


# ============================================================
# Partida de máquina no mata-mata
# ============================================================

def simulate_knockout_match(
    state: TournamentState, team_a: str, team_b: str, match_id: str
) -> MatchResult:
    """
    Simula uma partida sem alterar o estado do torneio.

    Os 90 minutos usam a mesma simulação da fase de grupos. Empate é decidido
    nos pênaltis, com gerador próprio Random(derive_seed(seed, match_id,
    "penalties")), que não consome o gerador da partida. O placar dos 90
    minutos é preservado; os pênaltis ficam em `result.penalties`.
    """
    match = simulate_machine_match_state(state, team_a, team_b, match_id)
    goals_a, goals_b = match.score["A"], match.score["B"]

    penalties = None
    if goals_a == goals_b:
        penalties = simulate_penalty_shootout(
            match.teams["A"].players,   # escalação ao fim dos 90 minutos
            match.teams["B"].players,
            state.config.penalties,
            rng=random.Random(derive_seed(state.config.seed, match_id, "penalties")),
        )
    return MatchResult(goals_a, goals_b, tuple(match.events), penalties)


def play_knockout_match(state: TournamentState, match_id: str) -> MatchRecord:
    """Joga uma partida pendente do mata-mata. Rejeições não alteram o estado."""
    record = state.match(match_id)
    if match_id not in KNOCKOUT_BRACKET:
        raise ValueError(f"A partida {match_id} não é do mata-mata.")
    if record.status is MatchStatus.ENCERRADA:
        raise ValueError(f"A partida {match_id} já foi jogada.")
    if record.team_a is None or record.team_b is None:
        raise ValueError(
            f"A partida {match_id} tem vaga indefinida "
            f"({record.slot_a} x {record.slot_b}) e não pode ser jogada."
        )
    if state.phase is not TournamentPhase.MATA_MATA:
        raise ValueError(
            f"O torneio está em {state.phase.value}, não na fase de mata-mata."
        )

    result = simulate_knockout_match(state, record.team_a, record.team_b, match_id)

    record.result = result            # commit só depois da simulação completa
    record.status = MatchStatus.ENCERRADA
    update_knockout_slots(state)
    _close_if_finished(state)
    return record


def _close_if_finished(state: TournamentState) -> None:
    if all(state.matches[i].status is MatchStatus.ENCERRADA for i in KNOCKOUT_ORDER):
        state.phase = TournamentPhase.ENCERRADO


# ============================================================
# Fim do torneio
# ============================================================

@dataclass(frozen=True)
class FinalRanking:
    champion: str
    runner_up: str
    third: str
    fourth: str


def final_ranking(state: TournamentState) -> FinalRanking:
    if state.phase is not TournamentPhase.ENCERRADO:
        raise ValueError("O torneio ainda não terminou.")
    final, third = state.matches["FINAL"], state.matches["THIRD"]
    return FinalRanking(
        champion=match_winner(final),
        runner_up=match_loser(final),
        third=match_winner(third),
        fourth=match_loser(third),
    )


def simulate_knockout(state: TournamentState) -> FinalRanking:
    """
    Joga, só por máquina, as partidas pendentes do mata-mata (iniciando-o se a
    fase de grupos já terminou) e fecha o torneio.
    """
    if state.phase is TournamentPhase.ENCERRADO:
        return final_ranking(state)
    if state.phase is TournamentPhase.GRUPOS:
        start_knockout(state)
    if state.phase is not TournamentPhase.MATA_MATA:
        raise ValueError("O torneio não está na fase de mata-mata.")

    update_knockout_slots(state)
    for match_id in KNOCKOUT_ORDER:
        if state.matches[match_id].status is MatchStatus.PENDENTE:
            play_knockout_match(state, match_id)
    return final_ranking(state)
