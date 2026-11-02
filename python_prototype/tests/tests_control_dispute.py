
import random

import pytest

from controll_dispute import (
    calculate_control_win_probability,
    control_win_probability,
    simulate_control_duel,
)


def test_equal_control_gives_equal_probability():
    assert control_win_probability(70, 70) == pytest.approx(0.5)


def test_higher_control_gives_higher_probability():
    assert control_win_probability(80, 60) > 0.5


def test_probabilities_are_symmetric():
    probability_a = control_win_probability(80, 60)
    probability_b = control_win_probability(60, 80)

    assert probability_a + probability_b == pytest.approx(1.0)


def test_invalid_control_raises_error():
    with pytest.raises(ValueError):
        control_win_probability(101, 50)


def test_invalid_scale_raises_error():
    with pytest.raises(ValueError):
        control_win_probability(70, 60, scale=0)


def test_simulation_is_reproducible():
    result_a = simulate_control_duel(
        70, 60, rng=random.Random(42)
    )
    result_b = simulate_control_duel(
        70, 60, rng=random.Random(42)
    )

    assert result_a == result_b


def test_extreme_control_advantage_makes_team_a_win_almost_always():
    prob_a, prob_b = calculate_control_win_probability(100, 0)

    assert prob_a == pytest.approx(1.0)
    assert prob_b == pytest.approx(0.0)

    wins = [simulate_control_duel(100, 0, rng=random.Random(seed)) for seed in range(100)]

    assert all(winner == "A" for winner in wins)

def test_less_extreme_control_advantage_still_favors_team_a():
    prob_a, prob_b = calculate_control_win_probability(90, 10)

    assert prob_a == pytest.approx(0.9)
    assert prob_b == pytest.approx(0.1)

    wins = [simulate_control_duel(90, 10, rng=random.Random(seed)) for seed in range(100)]

    assert all(winner in {"A", "B"} for winner in wins)
    assert wins.count("B") > 0
    assert wins.count("A") > 50
