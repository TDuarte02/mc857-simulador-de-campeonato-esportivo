import pytest

from copa_engine.cards import derive_cards
from copa_engine.collective_attributes import canonical_position
from copa_engine.derive import (
    INJURY_MAX_MATCHES,
    MatchLineups,
    derive_goals,
    derive_match_cards,
    display_minute,
    foul_minute,
    injury_matches,
)
from copa_engine.dynamics import DynamicsConfig
from copa_engine.match import CYCLE_MINUTES, MatchEventType as T, create_match, play_match
from copa_engine.rules import derive_seed
from tests.helpers import FORMATION_433, squad


def test_display_minute_formula():
    assert display_minute(30, 1, 1) == 37
    assert [display_minute(0, j, 3) for j in (1, 2, 3)] == [3, 7, 11]


def _play(seed, k=1):
    a, b = squad("A", 72), squad("B", 68)
    state = create_match(a, FORMATION_433, b, FORMATION_433)
    play_match(state, seed=seed, possessions_per_cycle=k, dynamics=DynamicsConfig())
    return state, MatchLineups.constant(a, b), tuple(state.events)


@pytest.mark.parametrize("k", [1, 3])
@pytest.mark.parametrize("seed", range(15))
def test_goals_follow_the_event_log(seed, k):
    state, lineups, events = _play(seed, k)
    goals = derive_goals(events, lineups, seed=seed, match_id="M")

    assert len(goals) == sum(state.score.values())
    for team in "AB":
        assert sum(g.team == team for g in goals) == state.score[team]
    for goal in goals:
        start = events[goal.event_index].minute
        assert events[goal.event_index].type is T.GOAL
        assert start <= goal.minute < start + CYCLE_MINUTES
        assert goal.player in lineups.at(goal.team, start)
        assert canonical_position(goal.player.pos) != "GK"


def test_goals_are_reproducible_and_depend_on_the_match_id():
    seeds_with_goals = [s for s in range(40) if sum(_play(s)[0].score.values()) >= 2]
    seed = seeds_with_goals[0]
    _, lineups, events = _play(seed)

    first = derive_goals(events, lineups, seed=seed, match_id="M")
    assert first == derive_goals(events, lineups, seed=seed, match_id="M")
    others = {
        tuple(g.player.name for g in derive_goals(events, lineups, seed=seed, match_id=f"M{i}"))
        for i in range(10)
    }
    assert len(others) > 1


@pytest.mark.parametrize("seed", range(10))
def test_cards_use_the_derived_seed_and_their_foul_minute_is_in_the_cycle(seed):
    _, lineups, events = _play(seed)

    cards = derive_match_cards(events, lineups, seed=seed, match_id="M")

    assert cards == derive_cards(events, lineups.at, seed=derive_seed(seed, "M", "cards"))
    for card in cards:
        foul = events[card.data["foul_event"]]
        assert foul.type is T.FALTA
        assert foul.minute <= foul_minute(events, card.data["foul_event"]) < foul.minute + CYCLE_MINUTES


def test_injury_duration_is_reproducible_and_bounded():
    durations = [injury_matches(7, "G-A-R1-1", player_id) for player_id in range(200)]

    assert durations == [injury_matches(7, "G-A-R1-1", player_id) for player_id in range(200)]
    assert set(durations) == set(range(1, INJURY_MAX_MATCHES + 1))


def test_lineups_switch_at_halftime():
    a, b, c = squad("A", 70), squad("B", 70), squad("C", 70)
    lineups = MatchLineups({"A": a, "B": b}, {"A": c, "B": b})

    assert lineups.at("A", 30) == a
    assert lineups.at("A", 45) == c
    assert MatchLineups.constant(a, b).at("B", 75) == tuple(b)
