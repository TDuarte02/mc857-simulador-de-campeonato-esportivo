"""
Mata-mata (Issue #35): chaves com vagas, simulação de partidas de máquina com
pênaltis para empates nos 90 minutos e fechamento do torneio.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from python_prototype.group_stage import (
    KNOCKOUT_BRACKET,
    KNOCKOUT_ORDER,
    MatchRecord,
    MatchResult,
    MatchStatus,
    SlotSource,
    TournamentPhase,
    TournamentState,
    build_knockout_schedule,
    group_standings,
    simulate_machine_match_state,
    match_winner, 
    match_loser, 
    _resolve,
    update_knockout_slots
)

from python_prototype.penalties import simulate_penalty_shootout
from python_prototype.tournament import derive_seed


def start_knockout(state: TournamentState) -> None:
    """Encerra a fase de grupos: preenche as vagas das quartas e passa o torneio ao mata-mata."""
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
