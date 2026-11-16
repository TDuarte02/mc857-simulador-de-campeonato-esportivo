
import pytest

from python_prototype.dispute import simulate_md5, simulate_md3


@pytest.mark.parametrize("seed", range(100))
def test_md5_always_ends_with_three_wins(seed):
    result = simulate_md5(
        control_a=70,
        control_b=60,
        rng=__import__("random").Random(seed),
    )

    assert result.winner in ("A", "B")
    assert max(result.wins_a, result.wins_b) == 3
    assert 3 <= len(result.duels) <= 5
    assert result.wins_a + result.wins_b == len(result.duels)


@pytest.mark.parametrize("seed", range(100))
def test_md3_always_ends_with_two_series(seed):
    result = simulate_md3(
        control_a=70,
        control_b=60,
        seed=seed,
    )

    assert result.winner in ("A", "B")
    assert max(result.wins_a, result.wins_b) == 2
    assert 2 <= len(result.series) <= 3


@pytest.mark.parametrize("seed", range(100))
def test_md3_series_are_valid_md5(seed):
    result = simulate_md3(
        control_a=70,
        control_b=60,
        seed=seed,
    )

    for md5 in result.series:
        assert md5.winner in ("A", "B")
        assert max(md5.wins_a, md5.wins_b) == 3
        assert 3 <= len(md5.duels) <= 5


def test_md3_is_reproducible():
    result_a = simulate_md3(70, 60, seed=42)
    result_b = simulate_md3(70, 60, seed=42)

    assert result_a == result_b


def test_rng_and_seed_cannot_be_used_together():
    import random

    with pytest.raises(ValueError):
        simulate_md3(
            70,
            60,
            rng=random.Random(42),
            seed=42,
        )
