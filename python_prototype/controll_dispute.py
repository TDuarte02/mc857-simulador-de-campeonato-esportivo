from __future__ import annotations

import random

DEFAULT_CONTROL_SCALE = 100.0


def _coerce_control_value(value, label: str) -> float:
    """Valida e converte um valor de controle para float."""
    if hasattr(value, "control"):
        value = value.control
    elif isinstance(value, dict):
        if "control" not in value:
            raise ValueError(f"O {label} não possui atributo 'control'.")
        value = value["control"]

    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Valor de Controle inválido para o {label}: {value!r}") from exc

    if numeric < 0:
        raise ValueError(f"O atributo de Controle do {label} não pode ser negativo.")

    return numeric


def control_win_probability(
    control_a: float,
    control_b: float,
    scale: float = DEFAULT_CONTROL_SCALE,
) -> float:
    """Retorna a probabilidade de o time A vencer um confronto de Controle."""
    if scale <= 0:
        raise ValueError("scale deve ser maior que zero.")

    ca = _coerce_control_value(control_a, "time A")
    cb = _coerce_control_value(control_b, "time B")

    if ca > scale or cb > scale:
        raise ValueError("Os atributos de Controle devem estar dentro da escala válida.")

    total = ca + cb
    if total <= 0:
        raise ValueError(
            "Os atributos de Controle devem somar um valor positivo para calcular a probabilidade."
        )

    probability_a = ca / total
    return probability_a


def calculate_control_win_probability(control_a, control_b, *, scale: float = DEFAULT_CONTROL_SCALE) -> tuple[float, float]:
    """Calcula as probabilidades para os times A e B."""
    pa = control_win_probability(control_a, control_b, scale=scale)
    return pa, 1.0 - pa


def calculate_victory_probability(control_a, control_b, *, scale: float = DEFAULT_CONTROL_SCALE) -> tuple[float, float]:
    """Alias do cálculo de probabilidades por Controle."""
    return calculate_control_win_probability(control_a, control_b, scale=scale)


def calculate_team_victory_probability(team_a, team_b, *, scale: float = DEFAULT_CONTROL_SCALE) -> tuple[float, float]:
    """Calcula a probabilidade a partir de TeamAttributes ou valores de Controle."""
    control_a = _coerce_control_value(team_a, "time A")
    control_b = _coerce_control_value(team_b, "time B")
    return calculate_control_win_probability(control_a, control_b, scale=scale)


def simulate_control_duel(
    control_a: float,
    control_b: float,
    rng: random.Random | None = None,
    *,
    seed: int | None = None,
    scale: float = DEFAULT_CONTROL_SCALE,
) -> str:
    """Simula um confronto e retorna 'A' ou 'B'."""
    probability_a = control_win_probability(control_a, control_b, scale=scale)
    random_generator = rng if rng is not None else random.Random(seed)
    return "A" if random_generator.random() < probability_a else "B"


def resolve_control_duel(
    control_a,
    control_b,
    *,
    rng: random.Random | None = None,
    seed: int | None = None,
    scale: float = DEFAULT_CONTROL_SCALE,
) -> str:
    """Alias para a resolução aleatória de um duelo de Controle."""
    return simulate_control_duel(control_a, control_b, rng=rng, seed=seed, scale=scale)


def determine_control_winner(
    control_a,
    control_b,
    *,
    rng: random.Random | None = None,
    seed: int | None = None,
    scale: float = DEFAULT_CONTROL_SCALE,
) -> str:
    """Alias para o vencedor do confronto."""
    return resolve_control_duel(control_a, control_b, rng=rng, seed=seed, scale=scale)
