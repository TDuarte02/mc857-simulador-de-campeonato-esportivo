import math
import random

import pytest

from python_prototype.control import control_win_probability, simulate_control_duel


def test_equal_control_gives_equal_probability():
    assert control_win_probability(70, 70) == pytest.approx(0.5)


def test_higher_control_gives_higher_probability():
    assert control_win_probability(80, 60) > 0.5


def test_probabilities_are_symmetric():
    assert control_win_probability(80, 60) + control_win_probability(60, 80) == pytest.approx(1.0)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, -1, 101])
def test_invalid_control_raises_error(bad):
    with pytest.raises(ValueError):
        control_win_probability(bad, 50)
    with pytest.raises(ValueError):
        control_win_probability(50, bad)
    with pytest.raises(ValueError):
        simulate_control_duel(bad, 50, seed=1)


def test_zero_vs_zero_raises_error():
    # Comportamento atual; pode mudar com a decisão do item 10.
    with pytest.raises(ValueError):
        control_win_probability(0, 0)


def test_simulation_is_reproducible():
    assert simulate_control_duel(70, 60, rng=random.Random(42)) == simulate_control_duel(
        70, 60, rng=random.Random(42)
    )


def test_rng_and_seed_cannot_be_used_together():
    with pytest.raises(ValueError):
        simulate_control_duel(70, 60, rng=random.Random(1), seed=1)


def test_extreme_control_advantage_makes_team_a_win_always():
    assert control_win_probability(100, 0) == pytest.approx(1.0)
    assert control_win_probability(0, 100) == pytest.approx(0.0)

    wins = [simulate_control_duel(100, 0, rng=random.Random(s)) for s in range(100)]
    assert all(w == "A" for w in wins)


def test_less_extreme_control_advantage_still_favors_team_a():
    assert control_win_probability(90, 10) == pytest.approx(0.9)

    wins = [simulate_control_duel(90, 10, rng=random.Random(s)) for s in range(100)]
    assert wins.count("B") > 0
    assert wins.count("A") > 50