import random

import pytest

from python_prototype.attack import (
    AttackOutcome,
    AttackParameters,
    calculate_attack_probabilities,
    resolve_attack_attempt,
    simulate_attack_sequence,
)


# ------------------------------------------------------------
# Parâmetros
# ------------------------------------------------------------

def test_default_parameters_match_experimental_values():
    params = AttackParameters()

    assert params.g_max == 0.30
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
    p = calculate_attack_probabilities(75, 25, attempt=1)
    q = 0.75

    assert p.goal == pytest.approx(0.30 * q)
    assert p.continuation == pytest.approx(0.50 * q)
    assert p.loss == pytest.approx(1 - 0.30 * q - 0.50 * q)


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

    assert p.loss == pytest.approx(0.0)
    assert p.goal + p.continuation == pytest.approx(1.0)


def test_continuation_probability_decreases_each_attempt():
    values = [calculate_attack_probabilities(70, 50, k).continuation for k in range(1, 10)]

    assert all(a > b for a, b in zip(values, values[1:]))


def test_loss_probability_increases_as_continuation_decreases():
    values = [calculate_attack_probabilities(70, 50, k).loss for k in range(1, 10)]

    assert all(a < b for a, b in zip(values, values[1:]))


def test_goal_probability_is_constant_across_attempts():
    goals = {calculate_attack_probabilities(70, 50, k).goal for k in range(1, 6)}

    assert len(goals) == 1


def test_zero_attack_always_loses_possession():
    p = calculate_attack_probabilities(0, 60, attempt=1)

    assert p.goal == 0.0
    assert p.continuation == 0.0
    assert p.loss == pytest.approx(1.0)


def test_invalid_inputs_raise_error():
    with pytest.raises(ValueError):
        calculate_attack_probabilities(-1, 50)
    with pytest.raises(ValueError):
        calculate_attack_probabilities(50, -1)
    with pytest.raises(ValueError):
        calculate_attack_probabilities(0, 0)
    with pytest.raises(ValueError):
        calculate_attack_probabilities(50, 50, attempt=0)


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


def test_sequence_always_terminates_even_with_slowest_decay():
    params = AttackParameters(g_max=0.0, c_max=1.0, r=0.99)

    for seed in range(50):
        result = simulate_attack_sequence(100, 1, params=params, seed=seed)
        assert result.outcome is AttackOutcome.POSSESSION_LOST


def test_sequence_result_does_not_touch_any_scoreboard():
    result = simulate_attack_sequence(70, 60, seed=7)

    assert not hasattr(result, "score")
    assert isinstance(result.is_goal, bool)


def test_stronger_attack_scores_more_often():
    def goals(attack, defense):
        return sum(
            simulate_attack_sequence(attack, defense, rng=random.Random(seed)).is_goal
            for seed in range(2000)
        )

    assert goals(90, 30) > goals(30, 90)
