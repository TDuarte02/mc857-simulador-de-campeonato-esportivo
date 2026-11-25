"""
Torneio com usuário (Issue #36): escolha da seleção, sessão de partida do
usuário, avanço do campeonato e resultado final serializável.

O usuário só decide a escalação da sua própria seleção em cada partida sua.
Partidas de máquina continuam dependendo apenas dos dois times, das
escalações padrão e da configuração: não importa se há usuário, nem em que
ordem elas são simuladas.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from python_prototype.collective_attributes import Player
from python_prototype.group_stage import (
    KNOCKOUT_ORDER,
    MatchRecord,
    MatchStatus,
    TournamentPhase,
    TournamentState,
    group_standings,
    play_machine_match,
)
from python_prototype.knockout import (
    FinalRanking,
    final_ranking,
    play_knockout_match,
    start_knockout,
)
from python_prototype.penalties import PenaltyShootout
from python_prototype.session import UserMatchSession
from python_prototype.tournament import (
    NationalTeam,
    TournamentConfig,
    setup_tournament,
)


class UserMatchPending(ValueError):
    """O torneio não avança: há uma partida do usuário pendente."""


def schedule_order(state: TournamentState) -> tuple[str, ...]:
    """
    Ordem cronológica das partidas: grupos rodada a rodada (R1 de todos os
    grupos, depois R2, depois R3) e, em seguida, o mata-mata.
    """
    group = [m for m in state.matches.values() if m.phase is TournamentPhase.GRUPOS]
    group.sort(key=lambda m: (m.round_number, m.group, m.match_id))
    return (*(m.match_id for m in group), *KNOCKOUT_ORDER)


class TournamentGame:
    """Torneio com (opcionalmente) uma seleção controlada pelo usuário."""

    def __init__(self, state: TournamentState, user_team: str | None = None) -> None:
        if user_team is not None and user_team not in state.teams:
            raise ValueError(f"Seleção desconhecida: {user_team!r}")
        self.state = state
        self.user_team = user_team
        self._session: UserMatchSession | None = None
        self._order = schedule_order(state)
        self._sync_phase()

    @classmethod
    def create(
        cls,
        config: TournamentConfig,
        teams: Sequence[NationalTeam] | None = None,
        user_team: str | None = None,
    ) -> "TournamentGame":
        """
        Cria o torneio (sorteio com `config.seed`). A escolha da seleção não
        altera o sorteio nem as sementes.
        """
        state = TournamentState.from_setup(setup_tournament(config, teams))
        return cls(state, user_team)

    # --- consulta ---------------------------------------------------------

    @property
    def phase(self) -> TournamentPhase:
        return self.state.phase

    @property
    def is_finished(self) -> bool:
        return self.state.phase is TournamentPhase.ENCERRADO

    @property
    def session(self) -> UserMatchSession | None:
        """Sessão do usuário em andamento, se houver."""
        return self._session

    def _involves_user(self, record: MatchRecord) -> bool:
        return self.user_team is not None and self.user_team in (
            record.team_a,
            record.team_b,
        )

    def next_match(self) -> MatchRecord | None:
        """Próxima partida pendente na ordem do calendário (None se encerrado)."""
        self._sync_phase()
        if self.is_finished:
            return None
        for match_id in self._order:
            record = self.state.matches[match_id]
            if record.status is MatchStatus.PENDENTE:
                if record.team_a is None or record.team_b is None:
                    raise ValueError(
                        f"A partida {match_id} tem vaga indefinida "
                        f"({record.slot_a} x {record.slot_b})."
                    )
                return record
        return None

    @property
    def pending_user_match(self) -> MatchRecord | None:
        """Primeira partida pendente do usuário com os dois times definidos."""
        if self.user_team is None:
            return None
        for match_id in self._order:
            record = self.state.matches[match_id]
            if record.status is MatchStatus.PENDENTE and self._involves_user(record):
                return record
        return None

    @property
    def user_eliminated(self) -> bool:
        """Fase de grupos concluída e nenhuma partida pendente com o usuário."""
        return (
            self.user_team is not None
            and self.state.group_stage_finished
            and self.pending_user_match is None
        )

    # --- partida do usuário ----------------------------------------------

    def start_user_match(
        self,
        players: Sequence[Player] | None = None,
        formation: Sequence[str] | None = None,
    ) -> UserMatchSession:
        """
        Abre a sessão da próxima partida pendente do usuário. Se informadas,
        `players` e `formation` valem como escalação desta partida; inválidas
        são rejeitadas sem abrir sessão nem alterar o estado.
        """
        if self.is_finished:
            raise ValueError("O torneio está encerrado e não aceita mais partidas.")
        if self._session is not None:
            raise ValueError("Já há uma partida do usuário em andamento.")
        if (players is None) != (formation is None):
            raise ValueError("Informe escalação e formação juntas.")
        record = self.pending_user_match
        if record is None:
            raise ValueError("O usuário não tem partida pendente.")

        session = UserMatchSession(
            self.state, record.match_id, self.user_team, on_commit=self._on_user_commit
        )
        if players is not None:
            session.change_lineup(players, formation)
        self._session = session
        return session

    def cancel_user_match(self) -> None:
        """Descarta a sessão aberta; a partida continua pendente."""
        if self._session is not None:
            self._session.cancel()
            self._session = None

    def play_user_match_auto(self) -> MatchRecord:
        """Joga a partida pendente do usuário sem nenhuma alteração."""
        session = self.start_user_match()
        session.play_to_end()
        return session.record

    def _on_user_commit(self, record: MatchRecord) -> None:
        self._session = None
        self._sync_phase()

    # --- avanço do torneio -----------------------------------------------

    def play_next_match(self) -> MatchRecord:
        """Simula a próxima partida pendente, se for de máquina."""
        self._require_no_session()
        record = self.next_match()
        if record is None:
            raise ValueError("O torneio está encerrado e não aceita mais partidas.")
        if self._involves_user(record):
            raise UserMatchPending(
                f"A partida {record.match_id} é do usuário e está pendente."
            )
        self._play_machine(record)
        return record

    def advance_to_user_match(self) -> MatchRecord | None:
        """
        Simula as partidas de máquina até a próxima partida do usuário, que é
        devolvida (ainda pendente). Devolve None se o torneio terminar antes,
        p. ex. com o usuário eliminado (ou sem usuário).
        """
        self._require_no_session()
        while True:
            record = self.next_match()
            if record is None or self._involves_user(record):
                return record
            self._play_machine(record)

    def simulate_to_end(self) -> FinalRanking:
        """
        Simula tudo até o fim. Com partida do usuário pendente (agora ou
        quando ela surgir no caminho), levanta `UserMatchPending`; o que já
        foi simulado antes continua válido.
        """
        self._require_no_session()
        if self.pending_user_match is not None:
            raise UserMatchPending("Há partida do usuário pendente.")
        while True:
            record = self.next_match()
            if record is None:
                break
            if self._involves_user(record):
                raise UserMatchPending(
                    f"A partida {record.match_id} é do usuário e está pendente."
                )
            self._play_machine(record)
        return final_ranking(self.state)

    # --- resultado --------------------------------------------------------

    def final_ranking(self) -> FinalRanking:
        return final_ranking(self.state)

    def final_result(self) -> dict[str, Any]:
        return build_final_result(self.state, self.user_team)

    def final_result_json(self, **kwargs: Any) -> str:
        return json.dumps(self.final_result(), **kwargs)

    # --- internos ---------------------------------------------------------

    def _require_no_session(self) -> None:
        if self._session is not None:
            raise UserMatchPending("Há uma partida do usuário em andamento.")

    def _play_machine(self, record: MatchRecord) -> None:
        if record.phase is TournamentPhase.GRUPOS:
            play_machine_match(self.state, record.match_id)
        else:
            play_knockout_match(self.state, record.match_id)
        self._sync_phase()

    def _sync_phase(self) -> None:
        """Passa ao mata-mata assim que a fase de grupos termina."""
        if (
            self.state.phase is TournamentPhase.GRUPOS
            and self.state.group_stage_finished
        ):
            start_knockout(self.state)


# ============================================================
# Resultado final serializável
# ============================================================

def _side_name(record: MatchRecord, side: str) -> str:
    return record.team_a if side == "A" else record.team_b


def _penalties_dict(record: MatchRecord, shootout: PenaltyShootout | None):
    if shootout is None:
        return None
    return {
        "first_team": _side_name(record, shootout.first_team),
        "goals_a": shootout.goals_a,
        "goals_b": shootout.goals_b,
        "winner": _side_name(record, shootout.winner),
        "sudden_death": shootout.sudden_death,
        "kicks": [
            {"team": _side_name(record, k.team), "player": k.player, "scored": k.scored}
            for k in shootout.kicks
        ],
    }


def _match_dict(record: MatchRecord) -> dict[str, Any]:
    result = record.result
    if result is None:
        raise ValueError(f"A partida {record.match_id} ainda não foi jogada.")
    if result.goals_a != result.goals_b:
        winner = record.team_a if result.goals_a > result.goals_b else record.team_b
    elif result.penalties is not None:
        winner = _side_name(record, result.penalties.winner)
    else:
        winner = None
    return {
        "id": record.match_id,
        "phase": record.phase.value,
        "group": record.group,
        "round": record.round_number,
        "slot_a": record.slot_a,
        "slot_b": record.slot_b,
        "team_a": record.team_a,
        "team_b": record.team_b,
        "goals_a": result.goals_a,
        "goals_b": result.goals_b,
        "penalties": _penalties_dict(record, result.penalties),
        "winner": winner,
    }


def build_final_result(
    state: TournamentState, user_team: str | None = None
) -> dict[str, Any]:
    """
    Resultado do torneio encerrado, só com tipos do JSON: campeão, vice, 3º e
    4º, tabelas dos grupos, partidas de grupo e chaves do mata-mata (placar
    dos 90 minutos e pênaltis à parte).
    """
    ranking = final_ranking(state)  # exige torneio ENCERRADO
    groups = {}
    for group in state.groups:
        standings = group_standings(state, group.name)
        groups[group.name] = [
            {
                "team": r.team,
                "played": r.played,
                "wins": r.wins,
                "draws": r.draws,
                "losses": r.losses,
                "goals_for": r.goals_for,
                "goals_against": r.goals_against,
                "goal_diff": r.goal_diff,
                "points": r.points,
            }
            for r in standings.rows
        ]

    group_matches = [
        _match_dict(m) for m in state.matches.values() if m.phase is TournamentPhase.GRUPOS
    ]
    knockout = [_match_dict(state.matches[i]) for i in KNOCKOUT_ORDER]
    return {
        "seed": state.config.seed,
        "user_team": user_team,
        "champion": ranking.champion,
        "runner_up": ranking.runner_up,
        "third": ranking.third,
        "fourth": ranking.fourth,
        "groups": groups,
        "group_matches": group_matches,
        "knockout": knockout,
    }
