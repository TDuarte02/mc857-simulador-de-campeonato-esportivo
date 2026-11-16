from __future__ import annotations

import random

from python_prototype.common import (
    ATTRIBUTE_MAX,
    TeamId,
    ensure_finite_non_negative,
    resolve_rng,
)


def control_win_probability(control_a: float, control_b: float) -> float:
    """
    Probabilidade de o time A vencer um duelo de Controle: C_A / (C_A + C_B).

    Levanta ValueError se algum valor não for finito, for negativo ou
    exceder ATTRIBUTE_MAX, ou se a soma for zero.
    """
    ca = ensure_finite_non_negative(control_a, "Controle do time A")
    cb = ensure_finite_non_negative(control_b, "Controle do time B")

    if ca > ATTRIBUTE_MAX or cb > ATTRIBUTE_MAX:
        raise ValueError(
            f"Os atributos de Controle devem estar em [0, {ATTRIBUTE_MAX:g}]."
        )

    total = ca + cb
    if total <= 0:
        raise ValueError(
            "Os atributos de Controle devem somar um valor positivo "
            "para calcular a probabilidade."
        )

    return ca / total


def simulate_control_duel(
    control_a: float,
    control_b: float,
    rng: random.Random | None = None,
    *,
    seed: int | None = None,
) -> TeamId:
    """Simula um duelo de Controle e devolve o vencedor, 'A' ou 'B'."""
    generator = resolve_rng(rng, seed)
    probability_a = control_win_probability(control_a, control_b)
    return "A" if generator.random() < probability_a else "B"