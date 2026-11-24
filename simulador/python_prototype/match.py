from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from collections.abc import Mapping, Sequence
from typing import Any

from python_prototype.common import (
    TEAM_IDS,
    TeamId,
    clamp,
    ensure_finite_non_negative,
    other_team,
    resolve_rng,
)

from python_prototype.attack import (
    AttackOutcome,
    AttackParameters,
    AttackSequenceResult,
    DEFAULT_ATTACK_PARAMETERS,
    simulate_attack_sequence,
)

from python_prototype.collective_attributes import (
    Player,
    TeamAttributes,
    calculate_team_attributes,
)

from python_prototype.dispute import MD3Result, simulate_md3
from python_prototype.dynamics import DynamicsConfig, DynamicsRuntime

# ============================================================
# Constantes
# ============================================================

CYCLE_MINUTES = 15
CYCLES_PER_MATCH = 6
HALFTIME_MINUTE = (CYCLES_PER_MATCH // 2) * CYCLE_MINUTES   # 45
FULL_TIME_MINUTE = CYCLES_PER_MATCH * CYCLE_MINUTES         # 90

MODIFIER_KEYS = ("attack", "defense", "control")

DEFAULT_RECOVERY_CONTROL_BONUS = 5.0

DEFAULT_POSSESSIONS_PER_CYCLE = 1
# ============================================================
# Estruturas
# ============================================================

class MatchPhase(str, Enum):
    FIRST_HALF = "FIRST_HALF"
    HALFTIME = "HALFTIME"
    SECOND_HALF = "SECOND_HALF"
    FINISHED = "FINISHED"


class MatchEventType(str, Enum):
    MD3_RESULT = "MD3_RESULT"
    ATTACK_SEQUENCE = "ATTACK_SEQUENCE"
    GOAL = "GOAL"
    POSSESSION_LOST = "POSSESSION_LOST"
    FALTA = "FALTA"
    LESAO = "LESAO"
    HALFTIME = "HALFTIME"
    LINEUP_CHANGE = "LINEUP_CHANGE"
    SECOND_HALF_START = "SECOND_HALF_START"
    FULL_TIME = "FULL_TIME"


@dataclass(frozen=True)
class MatchEvent:
    """
    Evento da partida.

    `minute` é o minuto simulado de INÍCIO do ciclo em que o evento
    ocorreu (os eventos de intervalo e fim de jogo usam 45 e 90).

    `data` guarda os dados estruturados do evento:
    - MD3_RESULT: wins_a, wins_b
    - ATTACK_SEQUENCE: attempts
    - FALTA (team = time infrator): cycle, possession, md5, duel
    - LESAO (team = time que sofreu a falta): player, cycle,
      foul_event (índice do evento FALTA de origem em `state.events`),
      effect (vazio nesta issue; reservado para uso futuro)
    - demais tipos: vazio
    """

    minute: int
    type: MatchEventType
    team: TeamId | None = None
    data: Mapping[str, Any] = field(default_factory=dict)

    @property
    def detail(self) -> str:
        """Descrição textual, derivada de `data` (para exibição)."""
        if self.type is MatchEventType.MD3_RESULT:
            return f"MD3 {self.data['wins_a']}x{self.data['wins_b']}"
        if self.type is MatchEventType.ATTACK_SEQUENCE:
            return f"{self.data['attempts']} tentativa(s)"
        if self.type is MatchEventType.FALTA:
            return f"ciclo {self.data['cycle']}, MD5 {self.data['md5']}, duelo {self.data['duel']}"
        if self.type is MatchEventType.LESAO:
            return f"{self.data['player']} (falta no evento {self.data['foul_event']})"
        return ""


@dataclass
class TeamState:
    """Time em campo: escalação, formação e atributos coletivos."""

    team_id: TeamId
    players: tuple[Player, ...]
    formation: tuple[str, ...]
    base: TeamAttributes
    # Ajustes aditivos temporários (efeitos). Nenhum é aplicado por padrão:
    # os efeitos pertinentes devem ser registrados explicitamente aqui.
    modifiers: dict[str, float] = field(
        default_factory=lambda: dict.fromkeys(MODIFIER_KEYS, 0.0)
    )

    @classmethod
    def from_lineup(
        cls, team_id: str, players: Sequence[Player], formation: Sequence[str]
    ) -> "TeamState":
        if team_id not in TEAM_IDS:
            raise ValueError(f"team_id deve ser 'A' ou 'B'; recebido: {team_id!r}")
        base = calculate_team_attributes(players, formation)
        return cls(team_id, tuple(players), tuple(formation), base)

    def _validate_modifiers(self) -> None:
        keys = set(self.modifiers)
        unknown = keys - set(MODIFIER_KEYS)
        missing = set(MODIFIER_KEYS) - keys
        if unknown or missing:
            raise ValueError(
                f"Modificadores inválidos para o time {self.team_id}: "
                f"desconhecidos={sorted(unknown)}, ausentes={sorted(missing)}."
            )
        for key, value in self.modifiers.items():
            if not math.isfinite(value):
                raise ValueError(
                    f"O modificador {key!r} do time {self.team_id} deve ser "
                    f"finito; recebido: {value!r}"
                )

    def effective(self) -> TeamAttributes:
        """Atributos efetivos do ciclo: base + modificadores, em [0, 100]."""
        self._validate_modifiers()
        return TeamAttributes(
            attack=clamp(self.base.attack + self.modifiers["attack"]),
            defense=clamp(self.base.defense + self.modifiers["defense"]),
            control=clamp(self.base.control + self.modifiers["control"]),
        )


@dataclass(frozen=True)
class PendingControlBonus:
    """Bônus de Controle pendente para a primeira MD5 da próxima disputa."""

    team: TeamId
    amount: float


@dataclass
class MatchState:
    teams: dict[TeamId, TeamState]
    cycle_index: int = 0  # ciclos já concluídos
    phase: MatchPhase = MatchPhase.FIRST_HALF
    score: dict[TeamId, int] = field(default_factory=lambda: {"A": 0, "B": 0})
    events: list[MatchEvent] = field(default_factory=list)
    pending_control_bonus: PendingControlBonus | None = None

    @property
    def clock(self) -> int:
        """Minuto simulado atual (derivado de `cycle_index`)."""
        return self.cycle_index * CYCLE_MINUTES

    @property
    def is_finished(self) -> bool:
        return self.phase is MatchPhase.FINISHED


@dataclass(frozen=True)
class PossessionResult:
    """Uma posse: MD3 -> sequência ofensiva do vencedor -> desfecho."""

    index: int  # número da posse dentro do ciclo, começando em 1
    md3: MD3Result
    attacking_team: TeamId
    attack: AttackSequenceResult
    scorer: TeamId | None
    applied_control_bonus: PendingControlBonus | None = None  # consumido nesta posse
    granted_control_bonus: PendingControlBonus | None = None  # gerado nesta posse

    @property
    def is_goal(self) -> bool:
        return self.scorer is not None


@dataclass(frozen=True)
class CycleResult:
    cycle: int  # número do ciclo, começando em 1
    start_minute: int
    end_minute: int
    possessions: tuple[PossessionResult, ...]

    # --- agregados ---
    @property
    def goals(self) -> int:
        return sum(p.is_goal for p in self.possessions)

    @property
    def scorers(self) -> tuple[TeamId, ...]:
        return tuple(p.scorer for p in self.possessions if p.scorer is not None)

    @property
    def is_goal(self) -> bool:
        return self.goals > 0

    # --- atalhos de compatibilidade (primeira posse) ---
    @property
    def md3(self) -> MD3Result:
        return self.possessions[0].md3

    @property
    def attacking_team(self) -> TeamId:
        return self.possessions[0].attacking_team

    @property
    def attack(self) -> AttackSequenceResult:
        return self.possessions[0].attack

    @property
    def scorer(self) -> TeamId | None:
        return self.possessions[0].scorer

    @property
    def applied_control_bonus(self) -> PendingControlBonus | None:
        """Bônus que vinha pendente do ciclo anterior (aplicado na 1ª posse)."""
        return self.possessions[0].applied_control_bonus

    @property
    def granted_control_bonus(self) -> PendingControlBonus | None:
        """Bônus que sai do ciclo (gerado pela última posse)."""
        return self.possessions[-1].granted_control_bonus


# ============================================================
# Criação e intervalo
# ============================================================

PossessionsSpec = int | tuple[int, int]


def _validate_possessions(value: PossessionsSpec) -> PossessionsSpec:
    """Aceita um inteiro >= 1 (fixo) ou (min, max) com 1 <= min <= max (sorteado)."""

    def valid_int(x: object) -> bool:
        return isinstance(x, int) and not isinstance(x, bool) and x >= 1

    if isinstance(value, tuple):
        if len(value) == 2 and all(valid_int(x) for x in value) and value[0] <= value[1]:
            return value
    elif valid_int(value):
        return value
    raise ValueError(
        "possessions_per_cycle deve ser um inteiro >= 1 ou um intervalo "
        f"(min, max) com 1 <= min <= max; recebido: {value!r}"
    )


def _draw_possessions(spec: PossessionsSpec, generator: random.Random) -> int:
    """K do ciclo: fixo, ou sorteado uniformemente em [min, max]."""
    if isinstance(spec, int):
        return spec
    lo, hi = spec
    if lo == hi:
        return lo  # sem sorteio: equivale a K fixo
    return lo + int(generator.random() * (hi - lo + 1))


def create_match(
    players_a: Sequence[Player],
    formation_a: Sequence[str],
    players_b: Sequence[Player],
    formation_b: Sequence[str],
) -> MatchState:
    return MatchState(
        teams={
            "A": TeamState.from_lineup("A", players_a, formation_a),
            "B": TeamState.from_lineup("B", players_b, formation_b),
        }
    )


def change_lineup(
    state: MatchState,
    team_id: TeamId,
    players: Sequence[Player],
    formation: Sequence[str],
) -> None:
    """Altera a escalação de um time. Só é permitido durante o intervalo."""
    if state.phase is not MatchPhase.HALFTIME:
        raise ValueError("Alterações na escalação só são permitidas no intervalo.")
    if team_id not in state.teams:
        raise ValueError(f"Time desconhecido: {team_id!r}")

    new_team = TeamState.from_lineup(team_id, players, formation)
    # Os modificadores (efeitos) do time são preservados.
    new_team.modifiers = dict(state.teams[team_id].modifiers)
    state.teams[team_id] = new_team
    state.events.append(
        MatchEvent(state.clock, MatchEventType.LINEUP_CHANGE, team_id)
    )


def start_second_half(state: MatchState) -> None:
    if state.phase is not MatchPhase.HALFTIME:
        raise ValueError("O segundo tempo só pode começar a partir do intervalo.")
    state.phase = MatchPhase.SECOND_HALF
    state.events.append(MatchEvent(state.clock, MatchEventType.SECOND_HALF_START))


# ============================================================
# Ciclo
# ============================================================

def run_cycle(
    state: MatchState,
    rng: random.Random | None = None,
    *,
    seed: int | None = None,
    attack_params: AttackParameters = DEFAULT_ATTACK_PARAMETERS,
    recovery_control_bonus: float = DEFAULT_RECOVERY_CONTROL_BONUS,
    possessions_per_cycle: PossessionsSpec = DEFAULT_POSSESSIONS_PER_CYCLE,
    dynamics: DynamicsRuntime | None = None,
) -> CycleResult:
    """
    Executa um ciclo de 15 minutos.

    `dynamics` (Issue #15) ativa moral, faltas e lesões; com `None` o
    comportamento é o da versão anterior. Os sorteios de falta e lesão
    usam os geradores próprios de `dynamics`, nunca `rng`. Se o ciclo
    falhar, `state` fica intacto (os geradores já consumidos não voltam).
    """
    if state.is_finished:
        raise ValueError("A partida já foi encerrada.")
    if state.phase is MatchPhase.HALFTIME:
        raise ValueError(
            "A partida está no intervalo: chame start_second_half antes de continuar."
        )

    spec = _validate_possessions(possessions_per_cycle)
    generator = resolve_rng(rng, seed)
    amount = ensure_finite_non_negative(
        recovery_control_bonus, "Bônus de recuperação de posse"
    )
    if dynamics is not None:
        dynamics.config.validate(attack_params)
    k = _draw_possessions(spec, generator)   # único ponto que consome RNG para o K
    start = state.clock
    cycle_number = state.cycle_index + 1
    new_clock = start + CYCLE_MINUTES
    new_phase = state.phase
    if new_clock >= FULL_TIME_MINUTE:
        new_phase = MatchPhase.FINISHED
    elif new_clock == HALFTIME_MINUTE:
        new_phase = MatchPhase.HALFTIME

    # ---- Fase 1: cálculo (não altera `state`) ----
    effective = {tid: team.effective() for tid, team in state.teams.items()}

    # Preparação: parâmetros ofensivos de cada time (moral calculada a partir
    # do placar no INÍCIO do ciclo; nunca acumulada).
    params_by_team = {
        tid: (
            attack_params
            if dynamics is None
            else dynamics.attack_params_for(
                attack_params, state.score[tid] - state.score[other_team(tid)]
            )
        )
        for tid in TEAM_IDS
    }
    foul_p = dynamics.foul_probability if dynamics is not None else 0.0
    foul_rng = dynamics.foul_rng if foul_p > 0 else None

    pending = state.pending_control_bonus
    possessions: list[PossessionResult] = []
    new_events: list[MatchEvent] = []

    for j in range(1, k + 1):
        applied = pending
        bonus_a = applied.amount if applied and applied.team == "A" else 0.0
        bonus_b = applied.amount if applied and applied.team == "B" else 0.0

        md3 = simulate_md3(
            effective["A"].control,
            effective["B"].control,
            rng=generator,
            first_md5_bonus_a=bonus_a,
            first_md5_bonus_b=bonus_b,
            foul_rng=foul_rng,
            foul_probability=foul_p,
        )
        attacker = md3.winner
        defender = other_team(attacker)

        # Faltas (e lesões decorrentes), em ordem cronológica, antes do MD3_RESULT.
        foul_events: list[MatchEvent] = []
        for md5_number, md5 in enumerate(md3.series, start=1):
            for foul in md5.fouls:
                foul_index = len(state.events) + len(new_events) + len(foul_events)
                foul_events.append(
                    MatchEvent(
                        start, MatchEventType.FALTA, foul.fouling_team,
                        {
                            "cycle": cycle_number,
                            "possession": j,
                            "md5": md5_number,
                            "duel": foul.duel,
                        },
                    )
                )
                if dynamics is not None:
                    victim = other_team(foul.fouling_team)
                    injured = dynamics.draw_injury(state.teams[victim].players)
                    if injured is not None:
                        foul_events.append(
                            MatchEvent(
                                start, MatchEventType.LESAO, victim,
                                {
                                    "player": injured.name,
                                    "cycle": cycle_number,
                                    "foul_event": foul_index,
                                    "effect": {},  # reservado; sem efeito por ora
                                },
                            )
                        )
        new_events += foul_events

        sequence = simulate_attack_sequence(
            effective[attacker].attack,
            effective[defender].defense,
            params=params_by_team[attacker],
            rng=generator,
        )
        scorer: TeamId | None = (
            attacker if sequence.outcome is AttackOutcome.GOAL else None
        )

        # Perda de posse gera bônus para o adversário, inclusive dentro do
        # ciclo; só é descartado se esta for a última posse da partida.
        granted: PendingControlBonus | None = None
        is_last_of_match = j == k and new_phase is MatchPhase.FINISHED
        if (
            sequence.outcome is AttackOutcome.POSSESSION_LOST
            and not is_last_of_match
            and amount > 0
        ):
            granted = PendingControlBonus(defender, amount)

        possessions.append(
            PossessionResult(j, md3, attacker, sequence, scorer, applied, granted)
        )
        new_events += [
            MatchEvent(start, MatchEventType.MD3_RESULT, attacker,
                       {"wins_a": md3.wins_a, "wins_b": md3.wins_b}),
            MatchEvent(start, MatchEventType.ATTACK_SEQUENCE, attacker,
                       {"attempts": sequence.attempts}),
            MatchEvent(start, MatchEventType.GOAL, scorer)
            if scorer is not None
            else MatchEvent(start, MatchEventType.POSSESSION_LOST, attacker),
        ]
        pending = granted  # consome o aplicado e encadeia o novo (nunca acumula)

    if new_phase is MatchPhase.FINISHED:
        new_events.append(MatchEvent(new_clock, MatchEventType.FULL_TIME))
    elif new_phase is MatchPhase.HALFTIME:
        new_events.append(MatchEvent(new_clock, MatchEventType.HALFTIME))

    # ---- Fase 2: commit ----
    for p in possessions:
        if p.scorer is not None:
            state.score[p.scorer] += 1
    state.events.extend(new_events)
    state.cycle_index += 1
    state.phase = new_phase
    state.pending_control_bonus = pending

    return CycleResult(
        cycle=state.cycle_index,
        start_minute=start,
        end_minute=new_clock,
        possessions=tuple(possessions),
    )


def play_match(
    state: MatchState,
    rng: random.Random | None = None,
    *,
    seed: int | None = None,
    attack_params: AttackParameters = DEFAULT_ATTACK_PARAMETERS,
    recovery_control_bonus: float = DEFAULT_RECOVERY_CONTROL_BONUS,
    possessions_per_cycle: PossessionsSpec = DEFAULT_POSSESSIONS_PER_CYCLE,
    dynamics: DynamicsConfig | None = None,
    dynamics_seed: int | None = None,
) -> list[CycleResult]:
    """
    Joga a partida até o fim, sem alterações no intervalo.

    `dynamics` ativa as mecânicas da Issue #15. A semente dos geradores de
    falta/lesão é `dynamics_seed` ou, se omitida, `seed`. Com `rng` e sem
    `dynamics_seed`, mecânicas aleatórias ligadas levantam ValueError.
    """
    if state.is_finished:
        raise ValueError("A partida já foi encerrada.")

    k = _validate_possessions(possessions_per_cycle)
    generator = resolve_rng(rng, seed)

    runtime: DynamicsRuntime | None = None
    if dynamics is not None:
        dynamics.validate(attack_params)
        runtime = DynamicsRuntime.create(
            dynamics, dynamics_seed if dynamics_seed is not None else seed
        )

    results: list[CycleResult] = []
    while not state.is_finished:
        if state.phase is MatchPhase.HALFTIME:
            start_second_half(state)
        results.append(
            run_cycle(
                state,
                generator,
                attack_params=attack_params,
                recovery_control_bonus=recovery_control_bonus,
                possessions_per_cycle=k,
                dynamics=runtime,
            )
        )
    return results


if __name__ == "__main__":
    def squad(prefix: str, rating: int) -> list[Player]:
        positions = ["GK", "RB", "CB", "CB", "LB", "CM", "CM", "CM", "RW", "ST", "LW"]
        return [
            Player(
                f"{prefix}{i}", pos, rating, rating, rating, rating, rating,
                rating, rating, rating, rating, rating, rating, rating,
                rating, rating, rating, rating, rating, rating,
            )
            for i, pos in enumerate(positions)
        ]

    formation = ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W", "W"]
    match = create_match(squad("A", 75), formation, squad("B", 65), formation)
    play_match(match, seed=42, dynamics=DynamicsConfig())
    print("Placar final:", match.score)
    for event in match.events:
        print(f"{event.minute:>2}' {event.type.value} {event.team or ''} {event.detail}")
