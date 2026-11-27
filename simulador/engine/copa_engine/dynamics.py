"""
Mecânicas dinâmicas da partida (Issue #15): moral (volatilidade), faltas e
lesões (apenas evento).

Toda a configuração fica em `DynamicsConfig`, e cada mecânica tem uma chave
`enabled` para ser desativada. Com tudo desativado (ou sem passar
`dynamics`), a partida se comporta exatamente como antes.
"""
from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass, field

from copa_engine.attack import AttackParameters
from copa_engine.collective_attributes import Player
from copa_engine.common import clamp


def _finite(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(f"{label} deve ser um número finito; recebido: {value!r}")
    return float(value)


def _probability(value: object, label: str) -> float:
    numeric = _finite(value, label)
    if not 0.0 <= numeric <= 1.0:
        raise ValueError(f"{label} deve estar em [0, 1]; recebido: {value!r}")
    return numeric


# ============================================================
# Configuração (único local)
# ============================================================

@dataclass(frozen=True)
class MoraleConfig:
    """M = `limit` (limite da moral); beta = sensibilidade da volatilidade."""

    enabled: bool = True
    limit: float = 2.0
    beta: float = 0.05

    def __post_init__(self) -> None:
        if _finite(self.limit, "Limite da moral (M)") < 0:
            raise ValueError("O limite da moral (M) não pode ser negativo.")
        if _finite(self.beta, "Sensibilidade (beta)") < 0:
            raise ValueError("A sensibilidade (beta) não pode ser negativa.")


@dataclass(frozen=True)
class FoulConfig:
    """Probabilidade de falta em cada confronto individual das MD5."""

    enabled: bool = True
    probability: float = 0.05

    def __post_init__(self) -> None:
        _probability(self.probability, "Probabilidade de falta")


@dataclass(frozen=True)
class InjuryConfig:
    """Probabilidade de lesão após cada falta (só gera evento)."""

    enabled: bool = True
    probability: float = 0.05

    def __post_init__(self) -> None:
        _probability(self.probability, "Probabilidade de lesão")


@dataclass(frozen=True)
class DynamicsConfig:
    morale: MoraleConfig = field(default_factory=MoraleConfig)
    fouls: FoulConfig = field(default_factory=FoulConfig)
    injuries: InjuryConfig = field(default_factory=InjuryConfig)

    @classmethod
    def disabled(cls) -> "DynamicsConfig":
        """Todas as mecânicas desligadas (resultados idênticos à versão anterior)."""
        return cls(
            MoraleConfig(enabled=False),
            FoulConfig(enabled=False),
            InjuryConfig(enabled=False),
        )

    def validate(self, attack_params: AttackParameters) -> None:
        """Validação ao carregar: levanta ValueError se a configuração for inválida."""
        validate_morale(attack_params, self.morale)


# ============================================================
# Moral
# ============================================================

def morale_value(goal_diff: float, config: MoraleConfig) -> float:
    """m = clamp(D, -M, +M)."""
    return clamp(goal_diff, -config.limit, config.limit)


def effective_attack_params(
    base: AttackParameters, goal_diff: float, config: MoraleConfig
) -> AttackParameters:
    """
    Parâmetros efetivos da sequência ofensiva do time atacante.

    v = beta*m; g_ef = g_max*(1+v); c_ef = c_max*(1-v); r não muda.
    Moral desligada ou m = 0 devolvem os parâmetros-base (mesmo objeto).
    """
    if not config.enabled:
        return base
    v = config.beta * morale_value(goal_diff, config)
    if v == 0:
        return base
    return AttackParameters(
        g_max=base.g_max * (1 + v),
        c_max=base.c_max * (1 - v),
        r=base.r,
    )


def validate_morale(base: AttackParameters, config: MoraleConfig) -> None:
    """
    Exige g_ef + c_ef <= 1 (e c_ef >= 0) para todo m em [-M, M].

    A soma é linear em m, então basta checar os extremos:
    pior caso = g + c + beta*M*|g - c| (0,82 com os valores iniciais).
    """
    if not config.enabled:
        return
    v_max = config.beta * config.limit
    if v_max > 1:
        raise ValueError(
            f"beta*M = {v_max:g} excede 1: o c_max efetivo ficaria negativo."
        )
    worst = base.g_max + base.c_max + v_max * abs(base.g_max - base.c_max)
    if worst > 1.0 + 1e-12:
        raise ValueError(
            f"Moral inválida: g_ef + c_ef chega a {worst:.4f} > 1 "
            "no pior caso (m = ±M)."
        )
    for edge in (-config.limit, config.limit):
        effective_attack_params(base, edge, config)  # AttackParameters revalida


# ============================================================
# Execução: geradores separados para faltas e lesões
# ============================================================

@dataclass
class DynamicsRuntime:
    """Configuração + geradores próprios (não tocam o RNG principal)."""

    config: DynamicsConfig
    foul_rng: random.Random
    injury_rng: random.Random

    @classmethod
    def create(cls, config: DynamicsConfig, seed: int | None) -> "DynamicsRuntime":
        if seed is None and (config.fouls.enabled or config.injuries.enabled):
            raise ValueError(
                "Faltas/lesões exigem semente própria: informe dynamics_seed "
                "(ou seed) ao jogar a partida."
            )
        return cls(
            config,
            random.Random(f"foul:{seed}"),
            random.Random(f"injury:{seed}"),
        )

    @property
    def foul_probability(self) -> float:
        return self.config.fouls.probability if self.config.fouls.enabled else 0.0

    def attack_params_for(
        self, base: AttackParameters, goal_diff: float
    ) -> AttackParameters:
        return effective_attack_params(base, goal_diff, self.config.morale)

    def draw_injury(self, players: Sequence[Player]) -> Player | None:
        """Após uma falta: sorteia se há lesão e, se houver, qual titular."""
        if not self.config.injuries.enabled:
            return None
        if self.injury_rng.random() >= self.config.injuries.probability:
            return None
        return players[int(self.injury_rng.random() * len(players))]
