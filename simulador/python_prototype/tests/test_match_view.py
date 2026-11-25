import pytest

from simulador.python_prototype.cards import derive_cards
from python_prototype.dynamics import DynamicsConfig
from python_prototype.match import MatchEventType as T, create_match, play_match
from simulador.python_prototype.match_view import MatchLineups, build_match_view, display_minute
from python_prototype.tests.helpers import FORMATION_433, squad


def test_display_minute_formula():
    assert display_minute(30, 1, 1) == 37
    assert [display_minute(0, j, 3) for j in (1, 2, 3)] == [3, 7, 11]


def _view(seed, k=1):
    a, b = squad("A", 72), squad("B", 68)
    state = create_match(a, FORMATION_433, b, FORMATION_433)
    play_match(state, seed=seed, possessions_per_cycle=k, dynamics=DynamicsConfig())
    lineups = MatchLineups.constant(a, b)
    events = tuple(state.events)
    cards = derive_cards(events, lineups.at, seed=seed)
    view = build_match_view(
        match_id="M", seed=seed, team_names={"A": "A", "B": "B"},
        events=events, card_events=cards, lineups=lineups,
    )
    return state, events, view


@pytest.mark.parametrize("k", [1, 3])
@pytest.mark.parametrize("seed", range(15))
def test_view_matches_event_log(seed, k):
    state, events, view = _view(seed, k)
    timeline = view["timeline"]

    assert view["score"] == state.score
    goals = [e for e in timeline if e["type"] == "GOAL"]
    assert len(goals) == sum(state.score.values())
    if goals:
        assert goals[-1]["score"] == state.score
    assert [e["minute"] for e in timeline] == sorted(e["minute"] for e in timeline)
    assert timeline[-1]["type"] == "FULL_TIME" and timeline[-1]["score"] == state.score
    assert not {"LESAO", "FALTA"} & {e["type"] for e in timeline}

    stats = view["stats"]
    for t in "AB":
        assert stats[t]["goals"] == state.score[t]
        assert stats[t]["fouls"] == sum(e.type is T.FALTA and e.team == t for e in events)
        assert stats[t]["attacks"] == sum(e.type is T.ATTACK_SEQUENCE and e.team == t for e in events)
        assert stats[t]["possession_lost"] == sum(e.type is T.POSSESSION_LOST and e.team == t for e in events)
    assert stats["A"]["possession"] + stats["B"]["possession"] == pytest.approx(100, abs=0.2)
    assert stats["A"]["attacks"] + stats["B"]["attacks"] == k * 6


def test_view_is_reproducible():
    assert _view(5)[2] == _view(5)[2]
