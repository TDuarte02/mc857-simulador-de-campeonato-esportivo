from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum

from copa_engine.common import ensure_finite_non_negative, resolve_rng


# ============================================================
# Parâmetros configuráveis
# ============================================================

@dataclass(frozen=True)
class AttackParameters:
    """
    Parâmetros da sequência ofensiva.

    - g_max: parâmetro-base de gol.
    - c_max: parâmetro-base de continuação.
    - r: fator de decaimento da continuação (0 < r < 1).

    Valida os parâmetros na criação, garantindo que
    P_G + P_C(k) <= 1 para qualquer q e k (o pior caso é q = 1, k = 1).
    """

    g_max: float = 0.30
    c_max: float = 0.50
    r: float = 0.75

    def __post_init__(self) -> None:
        if not 0.0 <= self.g_max <= 1.0:
            raise ValueError(f"g_max deve estar em [0, 1]; recebido: {self.g_max!r}")
        if not 0.0 <= self.c_max <= 1.0:
            raise ValueError(f"c_max deve estar em [0, 1]; recebido: {self.c_max!r}")
        if not 0.0 < self.r < 1.0:
            raise ValueError(f"r deve estar em (0, 1); recebido: {self.r!r}")
        if self.g_max + self.c_max > 1.0:
            raise ValueError(
                "g_max + c_max não pode exceder 1, "
                "ou a probabilidade de perda de posse ficaria negativa."
            )


DEFAULT_ATTACK_PARAMETERS = AttackParameters()


# ============================================================
# Estruturas de resultado
# ============================================================

class AttackOutcome(str, Enum):
    GOAL = "GOAL"
    CONTINUE = "CONTINUE"
    POSSESSION_LOST = "POSSESSION_LOST"


@dataclass(frozen=True)
class AttackProbabilities:
    goal: float
    continuation: float
    loss: float


@dataclass(frozen=True)
class AttackSequenceResult:
    """
    Resultado de uma sequência ofensiva.

    O motor NÃO atualiza o placar: quem recebe este resultado
    (componente da partida) decide o que fazer com ele.

    - outcome: desfecho final (GOAL ou POSSESSION_LOST).
    - attempts: número de tentativas realizadas.
    - history: desfecho de cada tentativa, em ordem.
    """

    outcome: AttackOutcome
    attempts: int
    history: tuple[AttackOutcome, ...]

    @property
    def is_goal(self) -> bool:
        return self.outcome is AttackOutcome.GOAL


# ============================================================
# Cálculo das probabilidades
# ============================================================


def attack_quality(attack: float, defense: float) -> float:
    """
    Calcula q = A / (A + D).

    Se Ataque e Defesa efetivos forem ambos zero, a razão é indefinida
    e q = 0.5.
    """
    a = ensure_finite_non_negative(attack, "Ataque efetivo")
    d = ensure_finite_non_negative(defense, "Defesa efetiva")

    total = a + d
    if total == 0:
        return 0.5

    return a / total


def calculate_attack_probabilities(
    attack: float,
    defense: float,
    attempt: int = 1,
    params: AttackParameters = DEFAULT_ATTACK_PARAMETERS,
) -> AttackProbabilities:
    """
    Calcula as probabilidades de gol, continuação e perda de posse
    para a tentativa `attempt` (começando em 1).

    P_G = g_max * q
    P_C(k) = c_max * r^(k-1) * q
    P_L(k) = 1 - P_G - P_C(k)
    """
    if attempt < 1:
        raise ValueError("A tentativa deve começar em 1.")

    q = attack_quality(attack, defense)

    goal = params.g_max * q
    continuation = params.c_max * (params.r ** (attempt - 1)) * q
    # Proteção contra erro de ponto flutuante; a validação dos
    # parâmetros já garante que o valor exato é >= 0.
    loss = min(1.0, max(0.0, 1.0 - goal - continuation))

    return AttackProbabilities(goal=goal, continuation=continuation, loss=loss)


# ============================================================
# Sorteio e simulação
# ============================================================

def resolve_attack_attempt(
    attack: float,
    defense: float,
    attempt: int = 1,
    params: AttackParameters = DEFAULT_ATTACK_PARAMETERS,
    rng: random.Random | None = None,
    *,
    seed: int | None = None,
) -> AttackOutcome:
    """Sorteia o desfecho de uma única tentativa ofensiva."""
    random_generator = resolve_rng(rng, seed)
    probabilities = calculate_attack_probabilities(attack, defense, attempt, params)

    draw = random_generator.random()

    if draw < probabilities.goal:
        return AttackOutcome.GOAL
    if draw < probabilities.goal + probabilities.continuation:
        return AttackOutcome.CONTINUE
    return AttackOutcome.POSSESSION_LOST


def simulate_attack_sequence(
    attack: float,
    defense: float,
    params: AttackParameters = DEFAULT_ATTACK_PARAMETERS,
    rng: random.Random | None = None,
    *,
    seed: int | None = None,
) -> AttackSequenceResult:
    """
    Simula a sequência ofensiva após a vitória na MD3.

    A cada continuação o contador de tentativas é incrementado.
    A sequência termina em gol ou perda de posse.
    Com parâmetros válidos, termina com probabilidade 1, pois
    P_C(k) decai geometricamente.
    """
    random_generator = resolve_rng(rng, seed)

    attempt = 1
    history: list[AttackOutcome] = []

    while True:
        outcome = resolve_attack_attempt(
            attack, defense, attempt, params, rng=random_generator
        )
        history.append(outcome)

        if outcome is AttackOutcome.CONTINUE:
            attempt += 1
            continue

        return AttackSequenceResult(
            outcome=outcome,
            attempts=attempt,
            history=tuple(history),
        )


# ============================================================
# Exemplo de uso
# ============================================================

if __name__ == "__main__":
    # Rode com: python -m copa_engine.attack
    attack_value = 75.0   # Ataque efetivo do atacante
    defense_value = 60.0  # Defesa efetiva do adversário

    # 1) Probabilidades de cada tentativa com os parâmetros padrão
    print("Probabilidades por tentativa (A=75, D=60):")
    for k in range(1, 5):
        p = calculate_attack_probabilities(attack_value, defense_value, attempt=k)
        print(
            f"  k={k}: gol={p.goal:.3f} | "
            f"continuação={p.continuation:.3f} | perda={p.loss:.3f}"
        )

    # 2) Uma sequência reproduzível (seed fixa)
    result = simulate_attack_sequence(attack_value, defense_value, seed=42)
    print(f"\nSequência (seed=42): {result.outcome.value} "
          f"após {result.attempts} tentativa(s)")
    print("  histórico:", [o.value for o in result.history])

    # 3) Parâmetros customizados (ataque mais difícil de converter)
    strict = AttackParameters(g_max=0.20, c_max=0.40, r=0.60)
    result = simulate_attack_sequence(
        attack_value, defense_value, params=strict, rng=random.Random(7)
    )
    print(f"\nCom parâmetros customizados: {result.outcome.value} "
          f"após {result.attempts} tentativa(s)")

    # 4) O motor só retorna o resultado; o placar é responsabilidade da partida
    score = {"A": 0, "B": 0}
    if result.is_goal:
        score["A"] += 1
    print("Placar (atualizado pelo chamador):", score)

    # 5) Estimativa da taxa de gol em muitas sequências
    rng = random.Random(0)
    n = 10_000
    goals = sum(
        simulate_attack_sequence(attack_value, defense_value, rng=rng).is_goal
        for _ in range(n)
    )
    print(f"\nTaxa de gol em {n} sequências: {goals / n:.1%}")