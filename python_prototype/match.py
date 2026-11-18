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

# ============================================================
# Constantes
# ============================================================

CYCLE_MINUTES = 15
CYCLES_PER_MATCH = 6
HALFTIME_MINUTE = (CYCLES_PER_MATCH // 2) * CYCLE_MINUTES   # 45
FULL_TIME_MINUTE = CYCLES_PER_MATCH * CYCLE_MINUTES         # 90

MODIFIER_KEYS = ("attack", "defense", "control")

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


@dataclass
class MatchState:
    teams: dict[TeamId, TeamState]
    cycle_index: int = 0  # ciclos já concluídos
    phase: MatchPhase = MatchPhase.FIRST_HALF
    score: dict[TeamId, int] = field(default_factory=lambda: {"A": 0, "B": 0})
    events: list[MatchEvent] = field(default_factory=list)

    @property
    def clock(self) -> int:
        """Minuto simulado atual (derivado de `cycle_index`)."""
        return self.cycle_index * CYCLE_MINUTES

    @property
    def is_finished(self) -> bool:
        return self.phase is MatchPhase.FINISHED

@dataclass(frozen=True)
class CycleResult:
    cycle: int  # número do ciclo, começando em 1
    start_minute: int
    end_minute: int
    md3: MD3Result
    attacking_team: TeamId
    attack: AttackSequenceResult
    scorer: TeamId | None  # "A", "B" ou None

    @property
    def is_goal(self) -> bool:
        return self.scorer is not None


# ============================================================
# Criação e intervalo
# ============================================================

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
) -> CycleResult:
    """
    Executa um ciclo de 15 minutos.

    O ciclo é atômico: toda a simulação (atributos efetivos -> MD3 ->
    sequência ofensiva) acontece antes de qualquer alteração em `state`.
    Se algo falhar na simulação, o estado permanece intacto.
    """
    if state.is_finished:
        raise ValueError("A partida já foi encerrada.")
    if state.phase is MatchPhase.HALFTIME:
        raise ValueError(
            "A partida está no intervalo; chame start_second_half antes do próximo ciclo."
        )

    generator = resolve_rng(rng, seed)
    start = state.clock

    # ---- Fase 1: cálculo (não altera `state`) ----
    effective = {tid: team.effective() for tid, team in state.teams.items()}

    md3 = simulate_md3(
        effective["A"].control, effective["B"].control, rng=generator
    )
    attacker = md3.winner
    defender = other_team(attacker)

    sequence = simulate_attack_sequence(
        effective[attacker].attack,
        effective[defender].defense,
        params=attack_params,
        rng=generator,
    )

    scorer: TeamId | None = attacker if sequence.outcome is AttackOutcome.GOAL else None

    new_events = [
        MatchEvent(start, MatchEventType.MD3_RESULT, attacker,
                   {"wins_a": md3.wins_a, "wins_b": md3.wins_b}),
        MatchEvent(start, MatchEventType.ATTACK_SEQUENCE, attacker,
                   {"attempts": sequence.attempts}),
        MatchEvent(start, MatchEventType.GOAL, scorer)
        if scorer is not None
        else MatchEvent(start, MatchEventType.POSSESSION_LOST, attacker),
    ]

    new_clock = start + CYCLE_MINUTES
    new_phase = state.phase
    if new_clock >= FULL_TIME_MINUTE:
        new_phase = MatchPhase.FINISHED
        new_events.append(MatchEvent(new_clock, MatchEventType.FULL_TIME))
    elif new_clock == HALFTIME_MINUTE:
        new_phase = MatchPhase.HALFTIME
        new_events.append(MatchEvent(new_clock, MatchEventType.HALFTIME))

    # ---- Fase 2: commit (sem nada que possa falhar) ----
    if scorer is not None:
        state.score[scorer] += 1
    state.events.extend(new_events)
    state.cycle_index += 1
    state.phase = new_phase

    return CycleResult(
        cycle=state.cycle_index,
        start_minute=start,
        end_minute=new_clock,
        md3=md3,
        attacking_team=attacker,
        attack=sequence,
        scorer=scorer,
    )


def play_match(
    state: MatchState,
    rng: random.Random | None = None,
    *,
    seed: int | None = None,
    attack_params: AttackParameters = DEFAULT_ATTACK_PARAMETERS,
) -> list[CycleResult]:
    """Joga a partida até o fim, sem alterações no intervalo."""
    if state.is_finished:
        raise ValueError("A partida já foi encerrada.")

    generator = resolve_rng(rng, seed)
    results: list[CycleResult] = []
    while not state.is_finished:
        if state.phase is MatchPhase.HALFTIME:
            start_second_half(state)
        results.append(run_cycle(state, generator, attack_params=attack_params))
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
    play_match(match, seed=42)
    print("Placar final:", match.score)
    for event in match.events:
        print(f"{event.minute:>2}' {event.type.value} {event.team or ''} {event.detail}")
