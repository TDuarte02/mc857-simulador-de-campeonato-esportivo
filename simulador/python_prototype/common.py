"""Utilitários compartilhados pelos módulos do simulador."""
from __future__ import annotations

import math
import random
from typing import Final, Literal

ATTRIBUTE_MAX: Final[float] = 100.0

TeamId = Literal["A", "B"]
TEAM_IDS: Final[tuple[TeamId, ...]] = ("A", "B")


def other_team(team_id: TeamId) -> TeamId:
    """Devolve o time adversário."""
    return "B" if team_id == "A" else "A"


def clamp(value: float, low: float = 0.0, high: float = ATTRIBUTE_MAX) -> float:
    """Limita `value` ao intervalo [low, high]."""
    return max(low, min(high, value))


def resolve_rng(rng: random.Random | None, seed: int | None) -> random.Random:
    """
    Devolve o gerador a ser usado: `rng` se informado, senão um novo
    `random.Random(seed)`. Informar `rng` e `seed` juntos é erro.

    Obs.: quando `rng` é informado, o chamador mantém a propriedade dele;
    números já consumidos não são revertidos se a operação falhar depois.
    """
    if rng is not None and seed is not None:
        raise ValueError("Informe rng ou seed, não ambos.")
    return rng if rng is not None else random.Random(seed)


def ensure_finite_non_negative(value: float, label: str) -> float:
    """Converte para float e exige valor finito e não negativo."""
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Valor inválido para {label}: {value!r}") from exc
    if not math.isfinite(numeric):
        raise ValueError(f"{label} deve ser um número finito; recebido: {value!r}")
    if numeric < 0:
        raise ValueError(f"{label} não pode ser negativo.")
    return numeric