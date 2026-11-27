"""
Configuração única do motor (Issues #11, #13, #15, #41): parâmetros de ataque,
bônus de recuperação de posse, posses por ciclo, dinâmicas (faltas, lesões,
moral), pênaltis e cartões.

`possessions_per_cycle` é sempre passado explicitamente a `play_match`.
"""
from __future__ import annotations

from dataclasses import dataclass

from copa_engine.attack import DEFAULT_ATTACK_PARAMETERS, AttackParameters
from copa_engine.cards import DEFAULT_CARD_CONFIG, CardConfig
from copa_engine.common import ensure_finite_non_negative
from copa_engine.dynamics import DynamicsConfig
from copa_engine.match import (
    DEFAULT_POSSESSIONS_PER_CYCLE,
    DEFAULT_RECOVERY_CONTROL_BONUS,
    PossessionsSpec,
    _validate_possessions,
)
from copa_engine.penalties import DEFAULT_PENALTY_CONFIG, PenaltyConfig


@dataclass(frozen=True)
class EngineConfig:
    attack_params: AttackParameters = DEFAULT_ATTACK_PARAMETERS
    recovery_control_bonus: float = DEFAULT_RECOVERY_CONTROL_BONUS
    possessions_per_cycle: PossessionsSpec = DEFAULT_POSSESSIONS_PER_CYCLE
    dynamics: DynamicsConfig = DynamicsConfig()
    penalties: PenaltyConfig = DEFAULT_PENALTY_CONFIG
    cards: CardConfig = DEFAULT_CARD_CONFIG

    def __post_init__(self) -> None:
        if not isinstance(self.penalties, PenaltyConfig):
            raise ValueError(f"penalties deve ser um PenaltyConfig; recebido: {self.penalties!r}")
        if not isinstance(self.cards, CardConfig):
            raise ValueError(f"cards deve ser um CardConfig; recebido: {self.cards!r}")

        ensure_finite_non_negative(self.recovery_control_bonus, "Bônus de recuperação de posse")
        _validate_possessions(self.possessions_per_cycle)
        self.dynamics.validate(self.attack_params)


DEFAULT_ENGINE_CONFIG = EngineConfig()
