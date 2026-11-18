import pytest

from python_prototype.tests.helpers import make_lineup, make_player, squad


def test_make_player_sets_all_attributes_to_rating():
    p = make_player("X", "ST", 80)

    assert (p.pace, p.shooting, p.goalkeeping_reflexes, p.overall) == (80, 80, 80, 80)


def test_make_player_overrides_only_the_given_attributes():
    p = make_player("X", "ST", 70, shooting=95, defending=20)

    assert p.shooting == 95
    assert p.defending == 20
    assert p.passing == 70


def test_make_player_rejects_unknown_attribute():
    with pytest.raises(TypeError, match="shoting"):
        make_player("X", "ST", shoting=95)


def test_squad_names_and_size():
    team = squad("A", 75)

    assert [p.name for p in team] == [f"A{i}" for i in range(11)]
    assert len({p.name for p in make_lineup(["GK"] * 3)}) == 3

from python_prototype.tests.helpers import ScriptedRandom


def test_scripted_random_returns_draws_in_order_and_tracks_usage():
    rng = ScriptedRandom([0.1, 0.2])

    assert (rng.random(), rng.random()) == (0.1, 0.2)
    assert rng.used == 2
    assert rng.remaining == 0


def test_scripted_random_fails_loudly_when_exhausted():
    rng = ScriptedRandom([0.1])
    rng.random()

    with pytest.raises(AssertionError, match="esgotada"):
        rng.random()