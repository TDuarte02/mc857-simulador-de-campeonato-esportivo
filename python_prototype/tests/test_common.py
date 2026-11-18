import random

import pytest

from python_prototype.common import (
    ATTRIBUTE_MAX,
    clamp,
    ensure_finite_non_negative,
    other_team,
    resolve_rng,
)


def test_other_team_swaps_ids():
    assert other_team("A") == "B"
    assert other_team("B") == "A"


@pytest.mark.parametrize("value,expected", [(-5, 0.0), (0, 0.0), (50, 50), (100, 100), (150, ATTRIBUTE_MAX)])
def test_clamp_limits_to_attribute_scale(value, expected):
    assert clamp(value) == expected


def test_resolve_rng_returns_given_rng_unchanged():
    rng = random.Random(1)
    assert resolve_rng(rng, None) is rng


def test_resolve_rng_with_seed_is_reproducible():
    assert resolve_rng(None, 7).random() == random.Random(7).random()


def test_resolve_rng_rejects_both():
    with pytest.raises(ValueError, match="rng ou seed"):
        resolve_rng(random.Random(1), 1)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1, "abc", None])
def test_ensure_finite_non_negative_rejects_invalid(bad):
    with pytest.raises(ValueError):
        ensure_finite_non_negative(bad, "x")


def test_ensure_finite_non_negative_accepts_zero_and_numeric_strings():
    assert ensure_finite_non_negative(0, "x") == 0.0
    assert ensure_finite_non_negative("12.5", "x") == 12.5