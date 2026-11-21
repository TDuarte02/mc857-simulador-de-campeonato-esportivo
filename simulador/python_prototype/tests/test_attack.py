import dataclasses
import math
import random

import pytest

from python_prototype.attack import (
    AttackOutcome,
    AttackParameters,
    attack_quality,
    calculate_attack_probabilities,
    resolve_attack_attempt,
    simulate_attack_sequence,
)


# ------------------------------------------------------------
# Parâmetros
# ------------------------------------------------------------

def test_default_parameters_match_calibrated_values():
    params = AttackParameters()

    assert params.g_max == 0.40
    assert params.c_max == 0.50
    assert params.r == 0.75


@pytest.mark.parametrize(
    "kwargs",
    [
        {"g_max": -0.1},
        {"g_max": 1.1},
        {"c_max": -0.1},
        {"c_max": 1.1},
        {"r": 0.0},
        {"r": 1.0},
        {"r": 1.5},
        {"g_max": 0.6, "c_max": 0.6},
    ],
)
def test_invalid_parameters_raise_error(kwargs):
    with pytest.raises(ValueError):
        AttackParameters(**kwargs)


def test_custom_parameters_are_used():
    params = AttackParameters(g_max=0.2, c_max=0.4, r=0.5)
    p = calculate_attack_probabilities(60, 60, attempt=2, params=params)

    assert p.goal == pytest.approx(0.2 * 0.5)
    assert p.continuation == pytest.approx(0.4 * 0.5 * 0.5)


# ------------------------------------------------------------
# Probabilidades
# ------------------------------------------------------------

def test_probabilities_match_formulas_for_first_attempt():
    # A qualidade q vem da própria função; o teste verifica a ESTRUTURA das
    # fórmulas (P_G = g_max * q, P_C = c_max * q), não o valor de q.
    params = AttackParameters()
    p = calculate_attack_probabilities(75, 25, attempt=1, params=params)
    q = attack_quality(75, 25)

    assert p.goal == pytest.approx(params.g_max * q)
    assert p.continuation == pytest.approx(params.c_max * q)
    assert p.loss == pytest.approx(1 - params.g_max * q - params.c_max * q)


@pytest.mark.parametrize("attack,defense", [(0, 50), (50, 0), (50, 50), (100, 1), (1, 100)])
@pytest.mark.parametrize("attempt", [1, 2, 5, 20])
def test_probabilities_sum_to_one_and_stay_in_range(attack, defense, attempt):
    p = calculate_attack_probabilities(attack, defense, attempt)

    for value in (p.goal, p.continuation, p.loss):
        assert 0.0 <= value <= 1.0
    assert p.goal + p.continuation + p.loss == pytest.approx(1.0)


def test_extreme_valid_parameters_keep_probabilities_valid():
    params = AttackParameters(g_max=0.5, c_max=0.5, r=0.99)
    p = calculate_attack_probabilities(100, 0, attempt=1, params=params)

    # Com a logística q se aproxima de 1 mas nunca chega lá, então a perda
    # não é exatamente zero — continua sendo um resíduo pequeno, e as três
    # probabilidades seguem somando 1.
    assert p.goal + p.continuation + p.loss == pytest.approx(1.0)
    assert p.loss >= 0.0
    assert p.loss < 0.05


def test_continuation_probability_decreases_each_attempt():
    values = [calculate_attack_probabilities(70, 50, k).continuation for k in range(1, 10)]

    assert all(a > b for a, b in zip(values, values[1:]))


def test_loss_probability_increases_as_continuation_decreases():
    values = [calculate_attack_probabilities(70, 50, k).loss for k in range(1, 10)]

    assert all(a < b for a, b in zip(values, values[1:]))


def test_goal_probability_is_constant_across_attempts():
    goals = {calculate_attack_probabilities(70, 50, k).goal for k in range(1, 6)}

    assert len(goals) == 1


def test_zero_attack_almost_always_loses_possession():
    # A logística nunca devolve q = 0, então um ataque nulo ainda converte uma
    # fração pequena. O que a regra garante é que a posse se perde na esmagadora
    # maioria das tentativas.
    p = calculate_attack_probabilities(0, 60, attempt=1)

    assert p.goal < 0.05
    assert p.continuation < 0.05
    assert p.loss > 0.90


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_non_finite_inputs_raise_error(bad):
    with pytest.raises(ValueError):
        calculate_attack_probabilities(bad, 50)
    with pytest.raises(ValueError):
        calculate_attack_probabilities(50, bad)
    with pytest.raises(ValueError):
        resolve_attack_attempt(bad, 50, seed=1)
    with pytest.raises(ValueError):
        simulate_attack_sequence(50, bad, seed=1)


@pytest.mark.parametrize("bad", [math.nan, math.inf])
def test_non_finite_parameters_raise_error(bad):
    for field in ("g_max", "c_max", "r"):
        with pytest.raises(ValueError):
            AttackParameters(**{field: bad})


def test_degenerate_case_without_continuation_keeps_probabilities_constant():
    # Sem continuação (c_max = 0), a probabilidade de continuar é zero em todas
    # as tentativas e a perda não varia: a monotonicidade estrita não se aplica.
    # (O caso "sem ataque" deixou de ser degenerado: a logística não produz q = 0.)
    params = AttackParameters(c_max=0.0)
    values = [calculate_attack_probabilities(60, 50, k, params) for k in (1, 2, 3)]

    assert all(v.continuation == 0.0 for v in values)
    assert len({v.loss for v in values}) == 1


def test_invalid_inputs_raise_error():
    with pytest.raises(ValueError):
        calculate_attack_probabilities(-1, 50)
    with pytest.raises(ValueError):
        calculate_attack_probabilities(50, -1)
    with pytest.raises(ValueError):
        calculate_attack_probabilities(50, 50, attempt=0)

def test_zero_attack_and_zero_defense_gives_even_quality():
    params = AttackParameters()
    p = calculate_attack_probabilities(0, 0, attempt=1, params=params)

    # A = D = 0 -> q = 0.5, a qualidade fica equilibrada entre os dois lados.
    assert p.goal == pytest.approx(params.g_max * 0.5)
    assert p.continuation == pytest.approx(params.c_max * 0.5)
    assert p.loss == pytest.approx(1 - params.g_max * 0.5 - params.c_max * 0.5)


def test_zero_vs_zero_sequence_terminates_and_is_reproducible():
    first = simulate_attack_sequence(0, 0, seed=5)
    second = simulate_attack_sequence(0, 0, seed=5)

    assert first == second
    assert first.outcome in (AttackOutcome.GOAL, AttackOutcome.POSSESSION_LOST)


# ------------------------------------------------------------
# Sorteio de uma tentativa
# ------------------------------------------------------------

class FixedRandom(random.Random):
    """RNG que devolve um valor fixo, para testar as transições."""

    def __init__(self, value: float):
        super().__init__()
        self._value = value

    def random(self) -> float:
        return self._value


def test_attempt_transitions_follow_draw_thresholds():
    # q = 0.5 -> P_G = 0.15, P_C(1) = 0.25, P_L = 0.60
    args = (50, 50, 1)

    assert resolve_attack_attempt(*args, rng=FixedRandom(0.10)) is AttackOutcome.GOAL
    assert resolve_attack_attempt(*args, rng=FixedRandom(0.20)) is AttackOutcome.CONTINUE
    assert resolve_attack_attempt(*args, rng=FixedRandom(0.50)) is AttackOutcome.POSSESSION_LOST
    assert resolve_attack_attempt(*args, rng=FixedRandom(0.999)) is AttackOutcome.POSSESSION_LOST


def test_attempt_rng_and_seed_cannot_be_used_together():
    with pytest.raises(ValueError):
        resolve_attack_attempt(50, 50, 1, rng=random.Random(1), seed=1)


# ------------------------------------------------------------
# Sequência
# ------------------------------------------------------------

@pytest.mark.parametrize("seed", range(200))
def test_sequence_ends_only_on_goal_or_loss(seed):
    result = simulate_attack_sequence(70, 60, seed=seed)

    assert result.outcome in (AttackOutcome.GOAL, AttackOutcome.POSSESSION_LOST)
    assert result.attempts == len(result.history)
    assert result.history[-1] is result.outcome
    # Nada de gol ou perda antes da última tentativa.
    assert all(o is AttackOutcome.CONTINUE for o in result.history[:-1])


def test_attempt_counter_increments_on_each_continuation():
    # Sorteio 0.20 -> continuação (q=0.5, 1ª tentativa); depois 0.99 -> perda.
    draws = iter([0.20, 0.99])

    class SequencedRandom(random.Random):
        def random(self) -> float:
            return next(draws)

    result = simulate_attack_sequence(50, 50, rng=SequencedRandom())

    assert result.history == (AttackOutcome.CONTINUE, AttackOutcome.POSSESSION_LOST)
    assert result.attempts == 2
    assert result.outcome is AttackOutcome.POSSESSION_LOST
    assert not result.is_goal


def test_sequence_allows_three_or_more_continuations():
    # q = 0.5: 0.20 < P_G + P_C(k) para k = 1, 2, 3 (0.40, 0.34, 0.30),
    # mas fica acima de P_G (0.15), logo é sempre continuação.
    draws = iter([0.20, 0.20, 0.20, 0.01])

    class SequencedRandom(random.Random):
        def random(self) -> float:
            return next(draws)

    result = simulate_attack_sequence(50, 50, rng=SequencedRandom())

    assert result.history == (
        AttackOutcome.CONTINUE,
        AttackOutcome.CONTINUE,
        AttackOutcome.CONTINUE,
        AttackOutcome.GOAL,
    )
    assert result.attempts == 4
    assert result.is_goal


def test_sequence_ends_in_goal_after_continuation():
    draws = iter([0.20, 0.01])

    class SequencedRandom(random.Random):
        def random(self) -> float:
            return next(draws)

    result = simulate_attack_sequence(50, 50, rng=SequencedRandom())

    assert result.history == (AttackOutcome.CONTINUE, AttackOutcome.GOAL)
    assert result.attempts == 2
    assert result.is_goal


def test_sequence_is_reproducible_with_seed():
    assert simulate_attack_sequence(70, 60, seed=42) == simulate_attack_sequence(70, 60, seed=42)


def test_sequence_rng_and_seed_cannot_be_used_together():
    with pytest.raises(ValueError):
        simulate_attack_sequence(70, 60, rng=random.Random(1), seed=1)


def test_probability_of_never_ending_goes_to_zero():
    # Pior caso para terminar: g_max = 0, c_max = 1, q = 1 e decaimento lento.
    # A chance de continuar até a tentativa n é o produto das P_C(k);
    # esse produto precisa tender a 0.
    params = AttackParameters(g_max=0.0, c_max=1.0, r=0.99)
    survival = 1.0
    for k in range(1, 301):
        survival *= calculate_attack_probabilities(100, 0, k, params).continuation

    assert survival < 1e-9


def test_sequences_terminate_even_with_slowest_decay():
    params = AttackParameters(g_max=0.0, c_max=1.0, r=0.99)

    attempts = [
        simulate_attack_sequence(100, 0, params=params, seed=seed).attempts
        for seed in range(200)
    ]

    assert all(a >= 1 for a in attempts)
    assert max(attempts) < 1000


def test_sequence_result_only_reports_the_outcome():
    result = simulate_attack_sequence(70, 60, seed=7)

    # O motor só informa o desfecho; o placar é do componente da partida.
    assert {f.name for f in dataclasses.fields(result)} == {"outcome", "attempts", "history"}
    assert isinstance(result.is_goal, bool)

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.outcome = AttackOutcome.GOAL


def test_stronger_attack_scores_more_often():
    def goals(attack, defense):
        return sum(
            simulate_attack_sequence(attack, defense, rng=random.Random(seed)).is_goal
            for seed in range(2000)
        )

    assert goals(90, 30) > goals(30, 90)