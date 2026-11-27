"""Testes da disputa de pênaltis (Issue #35)."""
import math
import random

import pytest

from copa_engine.penalties import (
    PenaltyConfig,
    conversion_probability,
    penalty_taker_order,
    simulate_penalty_shootout,
)
from tests.helpers import POSITIONS_433, ScriptedRandom, make_player, squad


def shooters(prefix="X"):
    """X10 é o melhor cobrador de linha; X0 é o goleiro."""
    return [
        make_player(f"{prefix}{i}", pos, 70, shooting=60 + i)
        for i, pos in enumerate(POSITIONS_433)
    ]


# ------------------------------------------------------------
# Configuração
# ------------------------------------------------------------

def test_default_config_matches_spec():
    c = PenaltyConfig()
    assert (c.p_base, c.s, c.p_min, c.p_max) == (0.75, 0.25, 0.50, 0.95)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"p_base": 1.2}, {"p_base": -0.1}, {"p_min": 0.8}, {"p_max": 0.7},
        {"s": -0.1}, {"p_base": math.nan}, {"s": math.inf}, {"p_base": True},
        {"p_base": "x"}, {"p_min": 0.0}, {"p_max": 1.0},
    ],
)
def test_invalid_config_is_rejected(kwargs):
    with pytest.raises(ValueError):
        PenaltyConfig(**kwargs)


def test_custom_valid_config_is_accepted():
    PenaltyConfig(p_base=0.8, s=0.0, p_min=0.6, p_max=0.9)


# ------------------------------------------------------------
# Probabilidade de conversão
# ------------------------------------------------------------

def test_equal_taker_and_keeper_gives_p_base():
    taker = make_player("T", "ST", 70)
    keeper = make_player("G", "GK", 70)
    assert conversion_probability(taker, keeper, PenaltyConfig()) == pytest.approx(0.75)


def test_better_taker_raises_and_better_keeper_lowers_probability():
    cfg = PenaltyConfig()
    keeper = make_player("G", "GK", 70)
    good = make_player("T", "ST", 70, shooting=90, mentality_penalties=90)   # S = 90
    bad = make_player("T", "ST", 70, shooting=50, mentality_penalties=50)    # S = 50
    assert conversion_probability(good, keeper, cfg) == pytest.approx(0.75 + 0.25 * 0.2)
    assert conversion_probability(bad, keeper, cfg) == pytest.approx(0.75 - 0.25 * 0.2)

    strong_keeper = make_player("G", "GK", 70, goalkeeping_reflexes=95)
    taker = make_player("T", "ST", 70)
    assert conversion_probability(taker, strong_keeper, cfg) < 0.75


def test_probability_is_clamped():
    cfg = PenaltyConfig()
    perfect = make_player("T", "ST", 100)
    useless = make_player("T", "ST", 0)
    weak_keeper = make_player("G", "GK", 0)
    great_keeper = make_player("G", "GK", 100)
    assert conversion_probability(perfect, weak_keeper, cfg) == cfg.p_max
    assert conversion_probability(useless, great_keeper, cfg) == cfg.p_min


# ------------------------------------------------------------
# Ordem dos cobradores
# ------------------------------------------------------------

def test_taker_order_is_by_score_desc_with_goalkeeper_last():
    order = penalty_taker_order(shooters())
    assert [p.name for p in order] == [f"X{i}" for i in range(10, 0, -1)] + ["X0"]


def test_taker_order_ties_follow_lineup_order():
    order = penalty_taker_order(squad("A", 70))
    assert [p.name for p in order] == [f"A{i}" for i in range(1, 11)] + ["A0"]


def test_lineup_without_goalkeeper_is_rejected():
    lineup = squad("A", 70)
    lineup[0] = make_player("A0", "CB", 70)
    with pytest.raises(ValueError, match="goleiro"):
        penalty_taker_order(lineup)


# ------------------------------------------------------------
# Disputa roteirizada (times 70 x 70: p = 0.75; 0.74 converte, 0.75 não)
# ------------------------------------------------------------

def test_early_finish_when_result_is_mathematically_decided():
    # A cobra primeiro: A converte 3, B erra 3. Após a 3ª de B: 3 > 0 + 2.
    rng = ScriptedRandom([0.1] + [0.74, 0.75] * 3)

    result = simulate_penalty_shootout(squad("A", 70), squad("B", 70), rng=rng)

    assert result.first_team == "A" and result.winner == "A"
    assert (result.goals_a, result.goals_b) == (3, 0)
    assert len(result.kicks) == 6 and not result.sudden_death
    assert rng.remaining == 0


def test_second_team_can_clinch_early():
    # B cobra primeiro e erra; A converte. Após a 3ª de A: 3 > 0 + 2.
    rng = ScriptedRandom([0.9] + [0.75, 0.74] * 3)

    result = simulate_penalty_shootout(squad("A", 70), squad("B", 70), rng=rng)

    assert result.first_team == "B" and result.winner == "A"
    assert len(result.kicks) == 6
    assert [k.team for k in result.kicks] == ["B", "A"] * 3
    assert rng.remaining == 0


def test_kicks_use_the_opponent_goalkeeper():
    keeper_b = make_player("B0", "GK", 70, goalkeeping_reflexes=100)
    team_b = [keeper_b] + squad("B", 70)[1:]
    # A: p = 0.75 + 0.25 * (70 - 100) / 100 = 0.675 (0.70 erra).
    # B: p = 0.75 (0.70 converte).
    rng = ScriptedRandom([0.1] + [0.70] * 6)

    result = simulate_penalty_shootout(squad("A", 70), team_b, rng=rng)

    assert result.winner == "B" and (result.goals_a, result.goals_b) == (0, 3)
    assert rng.remaining == 0


def test_sudden_death_after_five_each_ends_with_the_pair():
    # 10 cobranças convertidas (5 x 5); no par: A converte, B erra.
    rng = ScriptedRandom([0.1] + [0.0] * 10 + [0.0, 0.99])

    result = simulate_penalty_shootout(squad("A", 70), squad("B", 70), rng=rng)

    assert result.sudden_death and len(result.kicks) == 12
    assert (result.goals_a, result.goals_b) == (6, 5) and result.winner == "A"
    assert rng.remaining == 0          # o 2º time cobra mesmo com o 1º na frente


def test_sudden_death_continues_while_pairs_are_tied():
    rng = ScriptedRandom([0.1] + [0.0] * 10 + [0.0, 0.0] + [0.99, 0.0])

    result = simulate_penalty_shootout(squad("A", 70), squad("B", 70), rng=rng)

    assert len(result.kicks) == 14
    assert (result.goals_a, result.goals_b) == (6, 7) and result.winner == "B"
    assert rng.remaining == 0


def test_taker_order_restarts_after_the_eleventh_kick():
    lineup = shooters()
    rng = ScriptedRandom([0.1] + [0.0] * 10 + [0.0, 0.0] * 6 + [0.0, 0.99])

    result = simulate_penalty_shootout(lineup, shooters("Y"), rng=rng)

    names = [k.player for k in result.kicks_by("A")]
    assert len(names) == 12
    assert names[:5] == [f"X{i}" for i in range(10, 5, -1)]
    assert names[10] == "X0"                  # goleiro é o 11º
    assert names[11] == "X10"                 # recomeça
    assert rng.remaining == 0


# ------------------------------------------------------------
# Reprodutibilidade e invariantes
# ------------------------------------------------------------

def test_shootout_is_reproducible_and_rng_seed_are_exclusive():
    a, b = squad("A", 70), squad("B", 70)
    assert simulate_penalty_shootout(a, b, seed=5) == simulate_penalty_shootout(a, b, seed=5)
    with pytest.raises(ValueError):
        simulate_penalty_shootout(a, b, rng=random.Random(1), seed=1)


def _clinched(kicks):
    goals, taken = {"A": 0, "B": 0}, {"A": 0, "B": 0}
    for k in kicks:
        taken[k.team] += 1
        goals[k.team] += k.scored
    return any(
        goals[t] > goals[o] + 5 - taken[o] for t, o in (("A", "B"), ("B", "A"))
    ), goals


@pytest.mark.parametrize("seed", range(150))
def test_shootout_invariants(seed):
    a = squad("A", 50 + seed % 45)
    b = squad("B", 95 - seed % 45)

    r = simulate_penalty_shootout(a, b, seed=seed)

    assert r.goals_a == sum(k.scored for k in r.kicks_by("A"))
    assert r.goals_b == sum(k.scored for k in r.kicks_by("B"))
    assert r.goals_a != r.goals_b
    assert (r.winner == "A") == (r.goals_a > r.goals_b)
    first_n = len(r.kicks_by(r.first_team))
    second_n = len(r.kicks) - first_n
    assert 0 <= first_n - second_n <= 1
    assert all(
        k.team == (r.first_team if i % 2 == 0 else ("B" if r.first_team == "A" else "A"))
        for i, k in enumerate(r.kicks)
    )

    if len(r.kicks) <= 10:
        # só termina quando matematicamente decidido, e não antes
        assert _clinched(r.kicks)[0]
        assert not any(_clinched(r.kicks[:i])[0] for i in range(1, len(r.kicks)))
    else:
        assert len(r.kicks) % 2 == 0
        assert _goals_tied(r.kicks[:10])
        for end in range(12, len(r.kicks), 2):
            assert _goals_tied(r.kicks[:end])
        assert not _goals_tied(r.kicks)


def _goals_tied(kicks):
    goals = _clinched(kicks)[1]
    return goals["A"] == goals["B"]
