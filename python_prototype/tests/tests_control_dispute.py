
import random

import pytest

from controll_dispute import control_win_probability, simulate_control_duel


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
