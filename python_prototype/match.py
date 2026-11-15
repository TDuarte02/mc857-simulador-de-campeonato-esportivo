from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

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
    collective_attributes,
)
from python_prototype.dispute import MD3Result, simulate_md3

# ============================================================
# Constantes
# ============================================================

CYCLE_MINUTES = 15
CYCLES_PER_MATCH = 6
HALFTIME_MINUTE = 45
FULL_TIME_MINUTE = CYCLE_MINUTES * CYCLES_PER_MATCH  # 90

TEAM_IDS = ("A", "B")


def _other(team_id: str) -> str:
    return "B" if team_id == "A" else "A"


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
    """

    minute: int
    type: MatchEventType
    team: str | None = None
    detail: str = ""


@dataclass
class TeamState:
    """Time em campo: escalação, formação e atributos coletivos."""

    team_id: str
    players: tuple[Player, ...]
    formation: tuple[str, ...]
    base: TeamAttributes
    # Ajustes aditivos temporários (efeitos). Nenhum é aplicado por padrão:
    # os efeitos pertinentes devem ser registrados explicitamente aqui.
    modifiers: dict[str, float] = field(
        default_factory=lambda: {"attack": 0.0, "defense": 0.0, "control": 0.0}
    )

    @classmethod
    def from_lineup(
        cls, team_id: str, players: Sequence[Player], formation: Sequence[str]
    ) -> "TeamState":
        if team_id not in TEAM_IDS:
            raise ValueError(f"team_id deve ser 'A' ou 'B'; recebido: {team_id!r}")
        base = _to_team_attributes(collective_attributes(players, formation))
        return cls(team_id, tuple(players), tuple(formation), base)

    def effective(self) -> TeamAttributes:
        """Atributos efetivos do ciclo: base + modificadores, em [0, 100]."""

        def clamp(value: float) -> float:
            return max(0.0, min(100.0, value))

        return TeamAttributes(
            attack=clamp(self.base.attack + self.modifiers["attack"]),
            defense=clamp(self.base.defense + self.modifiers["defense"]),
            control=clamp(self.base.control + self.modifiers["control"]),
        )


def _to_team_attributes(values: dict[str, float]) -> TeamAttributes:
    return TeamAttributes(
        attack=values["attack"], defense=values["defense"], control=values["control"]
    )


@dataclass
class MatchState:
    teams: dict[str, TeamState]
    clock: int = 0
    cycle_index: int = 0  # ciclos já concluídos
    phase: MatchPhase = MatchPhase.FIRST_HALF
    score: dict[str, int] = field(default_factory=lambda: {"A": 0, "B": 0})
    events: list[MatchEvent] = field(default_factory=list)

    @property
    def is_finished(self) -> bool:
        return self.phase is MatchPhase.FINISHED


@dataclass(frozen=True)
class CycleResult:
    cycle: int  # número do ciclo, começando em 1
    start_minute: int
    end_minute: int
    md3: MD3Result
    attacking_team: str
    attack: AttackSequenceResult
    scorer: str | None  # "A", "B" ou None

    @property
    def is_goal(self) -> bool:
        return self.scorer is not None



