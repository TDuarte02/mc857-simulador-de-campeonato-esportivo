from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class OffenseParameters:
    """Parâmetros da sequência ofensiva."""

    goal_max: float = 0.30
    continuation_max: float = 0.50
    decay_factor: float = 0.75

    def __post_init__(self):
        values = (
            self.goal_max,
            self.continuation_max,
            self.decay_factor,
        )

        if not all(math.isfinite(value) for value in values):
            raise ValueError("Os parâmetros devem ser valores finitos.")

        if self.goal_max < 0 or self.continuation_max < 0:
            raise ValueError("As probabilidades-base não podem ser negativas.")

        if not 0 < self.decay_factor < 1:
            raise ValueError("O fator de decaimento deve estar entre 0 e 1.")

        if self.goal_max + self.continuation_max > 1:
            raise ValueError(
                "A soma das probabilidades-base não pode ultrapassar 1."
            )


@dataclass(frozen=True)
class OffenseProbabilities:
    """Probabilidades dos possíveis resultados de uma tentativa."""

    goal: float
    continuation: float
    possession_loss: float


@dataclass(frozen=True)
class OffenseAttempt:
    """Resultado de uma tentativa individual."""

    number: int
    probabilities: OffenseProbabilities
    outcome: str


@dataclass(frozen=True)
class OffenseResult:
    """Resultado completo de uma sequência ofensiva."""

    outcome: str
    attempts: tuple[OffenseAttempt, ...]

    @property
    def total_attempts(self) -> int:
        return len(self.attempts)


GOAL = "GOAL"
CONTINUATION = "CONTINUATION"
POSSESSION_LOSS = "POSSESSION_LOSS"


def _coerce_attribute(value, label: str) -> float:
    """Valida e converte um atributo efetivo para float."""

    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Valor inválido para {label}: {value!r}") from exc

    if not math.isfinite(numeric) or numeric < 0:
        raise ValueError(
            f"O atributo {label} deve ser finito e não negativo."
        )

    return numeric


def calculate_offense_probabilities(
    attack,
    defense,
    attempt: int = 1,
    parameters: OffenseParameters | None = None,
) -> OffenseProbabilities:
    """
    Calcula as probabilidades de gol, continuação e perda de posse.
    """

    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
        raise ValueError("A tentativa deve ser um inteiro positivo.")

    params = parameters or OffenseParameters()

    attack_value = _coerce_attribute(attack, "Ataque")
    defense_value = _coerce_attribute(defense, "Defesa")

    total = attack_value + defense_value

    if total <= 0:
        raise ValueError(
            "Ataque e Defesa devem somar um valor positivo."
        )

    q = attack_value / total

    probability_goal = params.goal_max * q

    probability_continuation = (
        params.continuation_max
        * params.decay_factor ** (attempt - 1)
        * q
    )

    probability_loss = (
        1.0 - probability_goal - probability_continuation
    )

    return OffenseProbabilities(
        goal=probability_goal,
        continuation=probability_continuation,
        possession_loss=probability_loss,
    )


def simulate_offense_attempt(
    attack,
    defense,
    attempt: int,
    rng: random.Random,
    parameters: OffenseParameters | None = None,
) -> OffenseAttempt:
    """Simula uma tentativa ofensiva individual."""

    probabilities = calculate_offense_probabilities(
        attack,
        defense,
        attempt,
        parameters,
    )

    draw = rng.random()

    if draw < probabilities.goal:
        outcome = GOAL

    elif draw < probabilities.goal + probabilities.continuation:
        outcome = CONTINUATION

    else:
        outcome = POSSESSION_LOSS

    return OffenseAttempt(
        number=attempt,
        probabilities=probabilities,
        outcome=outcome,
    )


def simulate_offense_sequence(
    attack,
    defense,
    rng: random.Random | None = None,
    *,
    seed: int | None = None,
    parameters: OffenseParameters | None = None,
) -> OffenseResult:
    """
    Simula uma sequência ofensiva completa.

    A sequência termina após um gol ou uma perda de posse.
    """

    if rng is not None and seed is not None:
        raise ValueError("Informe rng ou seed, não ambos.")

    random_generator = rng if rng is not None else random.Random(seed)

    attempts = []
    attempt_number = 1

    while True:
        result = simulate_offense_attempt(
            attack,
            defense,
            attempt_number,
            random_generator,
            parameters,
        )

        attempts.append(result)

        if result.outcome != CONTINUATION:
            return OffenseResult(
                outcome=result.outcome,
                attempts=tuple(attempts),
            )

        attempt_number += 1


if __name__ == "__main__":
    # Exemplo de uso
    parameters = OffenseParameters(
        goal_max=0.10,
        continuation_max=0.80,
        decay_factor=0.75,
    )

    result = simulate_offense_sequence(
        attack=80,
        defense=60,
        seed=15,
        parameters=parameters,
    )

    print(f"Resultado final: {result.outcome}")
    print(f"Número total de tentativas: {result.total_attempts}")
    for attempt in result.attempts:
        print(
            f"Tentativa {attempt.number}: "
            f"Probabilidades - Gol: {attempt.probabilities.goal:.2f}, "
            f"Continuação: {attempt.probabilities.continuation:.2f}, "
            f"Perda de posse: {attempt.probabilities.possession_loss:.2f} | "
            f"Resultado: {attempt.outcome}"
        )