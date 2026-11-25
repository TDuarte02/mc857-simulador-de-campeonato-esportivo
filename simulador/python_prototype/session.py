"""
Sessão de partida do usuário (Issue #36).

A sessão joga uma partida do torneio ciclo a ciclo, com o mesmo gerador e o
mesmo `DynamicsRuntime` que `play_match` criaria para a mesma partida
(`derive_seed(seed, match_id)` e `derive_seed(seed, match_id, "dynamics")`).
Sem alterações de escalação, o resultado é idêntico ao de `play_match`.

A escalação do usuário vale só para esta partida: `state.teams` do torneio
nunca é alterado. O resultado só entra no torneio quando a partida termina,
exatamente como o de uma partida de máquina (inclusive pênaltis no mata-mata).
"""
from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import replace

from python_prototype.collective_attributes import (
    POSITION_SECTORS,
    Player,
    canonical_position,
)
from python_prototype.dynamics import DynamicsRuntime
from python_prototype.group_stage import (
    MatchRecord,
    MatchResult,
    MatchStatus,
    TournamentPhase,
    TournamentState,
    update_knockout_slots,
)
from python_prototype.knockout import _close_if_finished
from python_prototype.match import (
    CycleResult,
    MatchPhase,
    TeamState,
    _validate_possessions,
    change_lineup as match_change_lineup,
    create_match,
    run_cycle,
    start_second_half as match_start_second_half,
)
from python_prototype.penalties import simulate_penalty_shootout
from python_prototype.tournament import NationalTeam, derive_seed

LINEUP_CHANGE_ERROR = (
    "Alterações na escalação só são permitidas antes do início e no intervalo."
)


# ============================================================
# Escalação do usuário
# ============================================================

def lineup_from_picks(
    team: NationalTeam, picks: Sequence[tuple[str, str]]
) -> tuple[tuple[Player, ...], tuple[str, ...]]:
    """
    Monta (jogadores, formação) a partir de pares (nome do jogador, slot).

    Os jogadores vêm do elenco da seleção e recebem a posição do slot; os
    originais não são alterados. A validação completa fica a cargo da sessão.
    """
    squad = {m.player.name: m for m in team.squad}
    players: list[Player] = []
    formation: list[str] = []
    for name, slot in picks:
        member = squad.get(name)
        if member is None:
            raise ValueError(f"{name!r} não pertence ao elenco de {team.name}.")
        players.append(replace(member.player, pos=slot))
        formation.append(slot)
    return tuple(players), tuple(formation)


def validate_lineup_from_squad(team: NationalTeam, players: Sequence[Player]) -> None:
    """
    Exige que cada jogador seja do elenco da seleção (mesmos atributos) e que
    a posição usada respeite as regras da Issue #33: goleiro só no gol, jogador
    de linha nunca no gol, e posição dentro de um setor do jogador.
    """
    squad = {m.player.name: m for m in team.squad}
    for player in players:
        member = squad.get(player.name)
        if member is None:
            raise ValueError(f"{player.name!r} não pertence ao elenco de {team.name}.")
        if replace(player, pos=member.player.pos) != member.player:
            raise ValueError(
                f"Os atributos de {player.name!r} diferem dos do elenco de {team.name}."
            )
        canon = canonical_position(player.pos)  # ValueError se desconhecida
        if (canon == "GK") != member.is_goalkeeper:
            raise ValueError(
                f"{player.name!r}: goleiro só pode jogar no gol, e jogador de "
                "linha não pode ser escalado como goleiro."
            )
        if POSITION_SECTORS[canon] not in member.sectors:
            raise ValueError(
                f"{player.name!r} não pode ser escalado como {player.pos!r} "
                "(setor incompatível com as suas posições)."
            )


# ============================================================
# Registro do resultado no torneio
# ============================================================

def commit_match_result(
    state: TournamentState, record: MatchRecord, result: MatchResult
) -> None:
    """
    Registra o resultado como `play_machine_match`/`play_knockout_match`:
    grava resultado e status, preenche as vagas do mata-mata e, ao fim do
    mata-mata, encerra o torneio.
    """
    record.result = result
    record.status = MatchStatus.ENCERRADA
    update_knockout_slots(state)
    if record.phase is TournamentPhase.MATA_MATA:
        _close_if_finished(state)


# ============================================================
# Sessão
# ============================================================

class UserMatchSession:
    """Partida do usuário, jogada ciclo a ciclo."""

    def __init__(
        self,
        state: TournamentState,
        match_id: str,
        user_team: str,
        *,
        on_commit: Callable[[MatchRecord], None] | None = None,
    ) -> None:
        record = state.match(match_id)
        if record.status is MatchStatus.ENCERRADA:
            raise ValueError(f"A partida {match_id} já foi jogada.")
        if record.team_a is None or record.team_b is None:
            raise ValueError(
                f"A partida {match_id} tem vaga indefinida "
                f"({record.slot_a} x {record.slot_b}) e não pode ser jogada."
            )
        if record.phase is not state.phase:
            raise ValueError(
                f"A partida {match_id} é da fase {record.phase.value}, "
                f"mas o torneio está em {state.phase.value}."
            )
        if user_team not in (record.team_a, record.team_b):
            raise ValueError(f"{user_team!r} não joga a partida {match_id}.")

        config = state.config
        config.dynamics.validate(config.attack_params)
        possessions = _validate_possessions(config.possessions_per_cycle)

        a, b = state.teams[record.team_a], state.teams[record.team_b]
        self.state = state
        self.record = record
        self.user_team = user_team
        self.user_side = "A" if record.team_a == user_team else "B"
        self.user_national_team = state.teams[user_team]
        self.match = create_match(a.lineup, a.formation, b.lineup, b.formation)
        self.cycles: list[CycleResult] = []
        self.result: MatchResult | None = None

        # Mesmos geradores e sementes de `simulate_machine_match_state`.
        self._generator = random.Random(derive_seed(config.seed, match_id))
        self._runtime = DynamicsRuntime.create(
            config.dynamics, derive_seed(config.seed, match_id, "dynamics")
        )
        self._possessions = possessions
        self._on_commit = on_commit
        self._closed = False

    # --- consulta ---------------------------------------------------------

    @property
    def match_id(self) -> str:
        return self.record.match_id

    @property
    def phase(self) -> MatchPhase:
        return self.match.phase

    @property
    def is_finished(self) -> bool:
        return self.match.is_finished

    @property
    def is_closed(self) -> bool:
        """True depois que o resultado entrou no torneio ou a sessão foi cancelada."""
        return self._closed

    @property
    def score(self) -> dict[str, int]:
        return dict(self.match.score)

    @property
    def user_lineup(self) -> tuple[Player, ...]:
        return self.match.teams[self.user_side].players

    @property
    def user_formation(self) -> tuple[str, ...]:
        return self.match.teams[self.user_side].formation

    @property
    def can_change_lineup(self) -> bool:
        return not self._closed and (
            self.match.cycle_index == 0 or self.match.phase is MatchPhase.HALFTIME
        )

    # --- escalação --------------------------------------------------------

    def change_lineup(self, players: Sequence[Player], formation: Sequence[str]) -> None:
        """
        Altera a escalação do usuário antes do início ou no intervalo.

        Toda a validação (elenco, setores, Issue #8) ocorre antes de qualquer
        mutação: entradas inválidas não alteram o estado.
        """
        self._require_open()
        if not self.can_change_lineup:
            raise ValueError(LINEUP_CHANGE_ERROR)
        players = tuple(players)
        validate_lineup_from_squad(self.user_national_team, players)

        if self.match.cycle_index == 0:
            # Antes do início: só troca o time em campo (sem evento).
            self.match.teams[self.user_side] = TeamState.from_lineup(
                self.user_side, players, formation
            )
        else:
            match_change_lineup(self.match, self.user_side, players, formation)

    # --- andamento --------------------------------------------------------

    def play_cycle(self) -> CycleResult:
        """Joga um ciclo de 15 minutos. No intervalo, chame `start_second_half`."""
        self._require_open()
        config = self.state.config
        result = run_cycle(
            self.match,
            self._generator,
            attack_params=config.attack_params,
            recovery_control_bonus=config.recovery_control_bonus,
            possessions_per_cycle=self._possessions,
            dynamics=self._runtime,
        )
        self.cycles.append(result)
        if self.match.is_finished:
            self._finish()
        return result

    def play_until_stop(self) -> list[CycleResult]:
        """Joga ciclos até o intervalo ou o fim da partida."""
        self._require_open()
        results: list[CycleResult] = []
        while not self.match.is_finished and self.match.phase is not MatchPhase.HALFTIME:
            results.append(self.play_cycle())
        return results

    def start_second_half(self) -> None:
        self._require_open()
        match_start_second_half(self.match)

    def play_to_end(self) -> MatchResult:
        """Joga o que falta (inclusive o início do 2º tempo) e registra o resultado."""
        self._require_open()
        while not self.match.is_finished:
            if self.match.phase is MatchPhase.HALFTIME:
                self.start_second_half()
            self.play_cycle()
        assert self.result is not None
        return self.result

    def cancel(self) -> None:
        """Descarta a sessão. O torneio não foi alterado, e a partida segue pendente."""
        self._closed = True

    # --- internos ---------------------------------------------------------

    def _require_open(self) -> None:
        if self._closed:
            raise ValueError("A sessão da partida já foi encerrada.")

    def _finish(self) -> None:
        record, match, config = self.record, self.match, self.state.config
        if record.status is MatchStatus.ENCERRADA:
            raise ValueError(f"A partida {record.match_id} já foi jogada.")

        goals_a, goals_b = match.score["A"], match.score["B"]
        penalties = None
        if record.phase is TournamentPhase.MATA_MATA and goals_a == goals_b:
            # Escalação ao fim dos 90 minutos; gerador próprio (não toca o da partida).
            penalties = simulate_penalty_shootout(
                match.teams["A"].players,
                match.teams["B"].players,
                config.penalties,
                rng=random.Random(derive_seed(config.seed, record.match_id, "penalties")),
            )
        result = MatchResult(goals_a, goals_b, tuple(match.events), penalties)

        commit_match_result(self.state, record, result)  # commit só após tudo calculado
        self.result = result
        self._closed = True
        if self._on_commit is not None:
            self._on_commit(record)
