import random

import pytest

from python_prototype.dispute import simulate_md3, simulate_md5
from python_prototype.tests.helpers import ScriptedRandom



@pytest.mark.parametrize("seed", range(100))
def test_md5_always_ends_with_three_wins(seed):
    result = simulate_md5(
        control_a=70,
        control_b=60,
        rng=random.Random(seed),
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

def test_md5_rng_and_seed_cannot_be_used_together():
    with pytest.raises(ValueError):
        simulate_md5(70, 60, rng=random.Random(42), seed=42)

# --- Roteiros determinísticos (controles 50 x 50: sorteio < 0.5 => A) ---

@pytest.mark.parametrize(
    "draws, winner, wins_a, wins_b, duels",
    [
        ([0.1, 0.1, 0.1], "A", 3, 0, ("A", "A", "A")),
        ([0.9, 0.9, 0.9], "B", 0, 3, ("B", "B", "B")),
        ([0.1, 0.9, 0.1, 0.9, 0.1], "A", 3, 2, ("A", "B", "A", "B", "A")),
        ([0.1, 0.9, 0.9, 0.1, 0.9], "B", 2, 3, ("A", "B", "B", "A", "B")),
    ],
)
def test_md5_follows_scripted_draws(draws, winner, wins_a, wins_b, duels):
    rng = ScriptedRandom(draws)

    result = simulate_md5(50, 50, rng=rng)

    assert (result.winner, result.wins_a, result.wins_b) == (winner, wins_a, wins_b)
    assert result.duels == duels
    assert rng.remaining == 0


def test_md5_stops_consuming_draws_once_decided():
    rng = ScriptedRandom([0.1, 0.1, 0.1, 0.9, 0.9])

    result = simulate_md5(50, 50, rng=rng)

    assert result.winner == "A"
    assert rng.remaining == 2


def test_md3_follows_scripted_series():
    # Série 1: A 3x0. Série 2: B 3x0. Série 3: A 3x0.
    rng = ScriptedRandom([0.1] * 3 + [0.9] * 3 + [0.1] * 3)

    result = simulate_md3(50, 50, rng=rng)

    assert result.winner == "A"
    assert (result.wins_a, result.wins_b) == (2, 1)
    assert tuple(s.winner for s in result.series) == ("A", "B", "A")
    assert rng.remaining == 0


def test_md3_ends_after_two_straight_series_wins():
    rng = ScriptedRandom([0.1] * 6 + [0.9] * 3)

    result = simulate_md3(50, 50, rng=rng)

    assert (result.wins_a, result.wins_b) == (2, 0)
    assert len(result.series) == 2
    assert rng.remaining == 3


# --- Consistência interna dos resultados ---

def test_md5_counters_match_duel_list():
    for seed in range(200):
        result = simulate_md5(70, 60, seed=seed)

        assert result.wins_a == result.duels.count("A")
        assert result.wins_b == result.duels.count("B")
        assert result.duels[-1] == result.winner


def test_md3_counters_match_series_winners():
    for seed in range(200):
        result = simulate_md3(70, 60, seed=seed)
        series_winners = [s.winner for s in result.series]

        assert result.wins_a == series_winners.count("A")
        assert result.wins_b == series_winners.count("B")
        assert series_winners[-1] == result.winner


# --- Casos extremos ---

@pytest.mark.parametrize("control_a, control_b, winner", [(100, 0, "A"), (0, 100, "B")])
def test_extreme_control_gap_wins_every_duel(control_a, control_b, winner):
    for seed in range(50):
        result = simulate_md3(control_a, control_b, seed=seed)

        assert result.winner == winner
        assert len(result.series) == 2
        assert all(md5.duels == (winner,) * 3 for md5 in result.series)


def test_zero_vs_zero_control_still_resolves_the_dispute():
    result = simulate_md3(0, 0, seed=1)

    assert result.winner in ("A", "B")
    assert 2 <= len(result.series) <= 3


# --- Frequência simulada x modelo analítico ---

def _md5_win_probability(p: float) -> float:
    """Primeiro a 3 vitórias: p^3 * (1 + 3q + 6q^2), com q = 1 - p."""
    q = 1 - p
    return p**3 * (1 + 3 * q + 6 * q**2)


def _md3_win_probability(s: float) -> float:
    """Primeiro a 2 séries: s^2 * (3 - 2s)."""
    return s**2 * (3 - 2 * s)


def test_md5_win_frequency_matches_binomial_model():
    # Controles 60 x 40 => p = 0.6 por duelo. Seed fixa: o teste é determinístico.
    rng = random.Random(12345)
    n = 20_000

    wins = sum(simulate_md5(60, 40, rng=rng).winner == "A" for _ in range(n))

    assert wins / n == pytest.approx(_md5_win_probability(0.6), abs=0.015)


def test_md3_win_frequency_matches_binomial_model():
    rng = random.Random(54321)
    n = 10_000
    expected = _md3_win_probability(_md5_win_probability(0.6))

    wins = sum(simulate_md3(60, 40, rng=rng).winner == "A" for _ in range(n))

    assert wins / n == pytest.approx(expected, abs=0.02)


def test_md5_three_duel_frequency_matches_model():
    # P(série em 3 duelos) = p^3 + q^3 = 0.216 + 0.064 = 0.28
    rng = random.Random(777)
    n = 20_000

    short = sum(len(simulate_md5(60, 40, rng=rng).duels) == 3 for _ in range(n))

    assert short / n == pytest.approx(0.28, abs=0.015)

def test_first_md5_bonus_applies_only_to_first_series():
    # 50x50 + bônus 50 para A na 1ª MD5 => p = 100/150 ≈ 0.667; depois p = 0.5.
    # Sorteio 0.6: A vence na 1ª MD5; B vence nas demais.
    rng = ScriptedRandom([0.6] * 9)

    result = simulate_md3(50, 50, rng=rng, first_md5_bonus_a=50)

    assert tuple(s.winner for s in result.series) == ("A", "B", "B")
    assert result.winner == "B"
    assert rng.remaining == 0


def test_first_md5_bonus_for_b_lowers_a_probability():
    rng = ScriptedRandom([0.4] * 9)   # sem bônus, 0.4 < 0.5 => A

    result = simulate_md3(50, 50, rng=rng, first_md5_bonus_b=50)

    assert tuple(s.winner for s in result.series) == ("B", "A", "A")


def test_bonus_is_clamped_to_attribute_max():
    result = simulate_md3(100, 0, seed=1, first_md5_bonus_a=50)

    assert result.winner == "A"


@pytest.mark.parametrize("bad", [-1, float("nan"), float("inf")])
def test_invalid_first_md5_bonus_is_rejected(bad):
    with pytest.raises(ValueError):
        simulate_md3(50, 50, seed=1, first_md5_bonus_a=bad)


def test_md3_without_bonus_is_unchanged():
    assert simulate_md3(70, 60, seed=42) == simulate_md3(
        70, 60, seed=42, first_md5_bonus_a=0.0, first_md5_bonus_b=0.0
    )