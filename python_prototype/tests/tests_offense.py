import random

import pytest

from offense import (
    OffenseParameters,
    calculate_offense_probabilities,
    simulate_offense_sequence,
    GOAL,
    CONTINUATION,
    POSSESSION_LOSS,
)


class FixedRNG:
    """Gerador determinístico para testes de transições."""

    def __init__(self, values):
        self.values = iter(values)

    def random(self):
        return next(self.values)


@pytest.fixture
def parameters():
    return OffenseParameters(
        goal_max=0.30,
        continuation_max=0.50,
        decay_factor=0.75,
    )


def test_probabilities_sum_to_one(parameters):
    probabilities = calculate_offense_probabilities(
        80, 60, parameters=parameters
    )

    total = (
        probabilities.goal
        + probabilities.continuation
        + probabilities.possession_loss
    )

    assert total == pytest.approx(1.0)


def test_probabilities_are_valid(parameters):
    probabilities = calculate_offense_probabilities(
        80, 60, parameters=parameters
    )

    assert 0 <= probabilities.goal <= 1
    assert 0 <= probabilities.continuation <= 1
    assert 0 <= probabilities.possession_loss <= 1


def test_continuation_probability_decreases(parameters):
    probabilities = [
        calculate_offense_probabilities(
            80, 60, attempt=k, parameters=parameters
        )
        for k in range(1, 5)
    ]

    continuations = [p.continuation for p in probabilities]

    assert continuations == sorted(continuations, reverse=True)
    assert all(
        a > b for a, b in zip(continuations, continuations[1:])
    )


def test_possession_loss_probability_increases(parameters):
    probabilities = [
        calculate_offense_probabilities(
            80, 60, attempt=k, parameters=parameters
        )
        for k in range(1, 5)
    ]

    losses = [p.possession_loss for p in probabilities]

    assert losses == sorted(losses)
    assert all(a < b for a, b in zip(losses, losses[1:]))


def test_goal_ends_sequence(parameters):
    rng = FixedRNG([0.0])

    result = simulate_offense_sequence(
        80, 60, rng=rng, parameters=parameters
    )

    assert result.outcome == GOAL
    assert result.total_attempts == 1


def test_possession_loss_ends_sequence(parameters):
    rng = FixedRNG([0.99])

    result = simulate_offense_sequence(
        80, 60, rng=rng, parameters=parameters
    )

    assert result.outcome == POSSESSION_LOSS
    assert result.total_attempts == 1


def test_continuation_increments_attempt_counter(parameters):
    # Primeira tentativa: continuação.
    # Segunda tentativa: gol.
    rng = FixedRNG([0.20, 0.10])

    result = simulate_offense_sequence(
        80, 60, rng=rng, parameters=parameters
    )

    assert result.outcome == GOAL
    assert result.total_attempts == 2

    assert result.attempts[0].outcome == CONTINUATION
    assert result.attempts[0].number == 1

    assert result.attempts[1].outcome == GOAL
    assert result.attempts[1].number == 2


def test_sequence_can_have_multiple_continuations(parameters):
    rng = FixedRNG([0.20, 0.20, 0.99])

    result = simulate_offense_sequence(
        80, 60, rng=rng, parameters=parameters
    )

    assert result.outcome == POSSESSION_LOSS
    assert result.total_attempts == 3

    assert [
        attempt.number for attempt in result.attempts
    ] == [1, 2, 3]


def test_seed_reproducibility(parameters):
    result_a = simulate_offense_sequence(
        80, 60, seed=42, parameters=parameters
    )

    result_b = simulate_offense_sequence(
        80, 60, seed=42, parameters=parameters
    )

    assert result_a == result_b


def test_rng_and_seed_cannot_be_used_together():
    with pytest.raises(ValueError):
        simulate_offense_sequence(
            80,
            60,
            rng=random.Random(42),
            seed=42,
        )


@pytest.mark.parametrize(
    "attack, defense",
    [
        (-10, 50),
        (50, -10),
        (0, 0),
        (float("inf"), 50),
        (50, float("nan")),
    ],
)
def test_invalid_attributes(attack, defense):
    with pytest.raises(ValueError):
        calculate_offense_probabilities(attack, defense)


@pytest.mark.parametrize(
    "attempt",
    [0, -1, 1.5, True],
)
def test_invalid_attempt(attempt):
    with pytest.raises(ValueError):
        calculate_offense_probabilities(80, 60, attempt)


@pytest.mark.parametrize(
    "goal, continuation, decay",
    [
        (-0.1, 0.5, 0.75),
        (0.3, -0.1, 0.75),
        (0.3, 0.5, 0),
        (0.3, 0.5, 1),
        (0.7, 0.5, 0.75),
        (float("nan"), 0.5, 0.75),
    ],
)
def test_invalid_parameters(goal, continuation, decay):
    with pytest.raises(ValueError):
        OffenseParameters(
            goal_max=goal,
            continuation_max=continuation,
            decay_factor=decay,
        )

