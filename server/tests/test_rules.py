from itertools import combinations

from api.config import Settings
from api.domain.models import (
    Card,
    CardType,
    Injury,
    Match,
    MatchResult,
    Player,
    PlayerStatus,
    Position,
    Stage,
    UnavailableReason,
)
from api.domain.rules import apply_match_events, best_lineup, compute_standings, round_robin


def played(home: str, away: str, home_goals: int, away_goals: int, cards=()) -> Match:
    result = MatchResult(home_goals, away_goals, cards=list(cards))
    return Match(f"{home}-{away}", "s", Stage.GROUP, 1, home, away, "A", result, played=True)


def test_round_robin_pairs_every_team_once():
    teams = ["a", "b", "c", "d"]
    rounds = round_robin(teams)

    assert len(rounds) == 3
    for fixtures in rounds:
        assert sorted(team for fixture in fixtures for team in fixture) == teams
    pairs = {frozenset(fixture) for fixtures in rounds for fixture in fixtures}
    assert pairs == {frozenset(pair) for pair in combinations(teams, 2)}


def test_standings_count_points_and_goals():
    table = compute_standings(["a", "b", "c"], [played("a", "b", 2, 0), played("b", "c", 1, 1)])

    assert [row.squad_id for row in table] == ["a", "c", "b"]
    leader, last = table[0], table[2]
    assert (leader.points, leader.won, leader.goal_difference) == (3, 1, 2)
    assert (last.played, last.drawn, last.lost, last.points) == (2, 1, 1, 1)


def test_standings_ignore_results_not_revealed_yet():
    hidden = played("a", "b", 5, 0)
    hidden.played = False

    assert all(row.played == 0 for row in compute_standings(["a", "b"], [hidden]))


def test_standings_break_ties_by_goal_difference_then_goals_then_cards():
    # a and b both win once; a by a larger margin.
    by_difference = compute_standings(
        ["a", "b", "c", "d"], [played("a", "c", 3, 0), played("b", "d", 1, 0)]
    )
    assert [row.squad_id for row in by_difference][:2] == ["a", "b"]

    # Same margin, b scored more.
    by_goals = compute_standings(["a", "b", "c", "d"], [played("a", "c", 1, 0), played("b", "d", 2, 1)])
    assert [row.squad_id for row in by_goals][:2] == ["b", "a"]

    # Identical scores, a took a red card.
    red = Card(40, 1, "a", CardType.RED)
    by_cards = compute_standings(
        ["a", "b", "c", "d"], [played("a", "c", 1, 0, [red]), played("b", "d", 1, 0)]
    )
    assert [row.squad_id for row in by_cards][:2] == ["b", "a"]


def test_red_card_suspends_for_one_match():
    statuses = {1: PlayerStatus(), 2: PlayerStatus()}
    settings = Settings()

    apply_match_events(statuses, MatchResult(0, 0, cards=[Card(10, 1, "x", CardType.RED)]), "x", settings)
    assert not statuses[1].available
    assert statuses[1].reason is UnavailableReason.SUSPENDED_RED
    assert statuses[2].available

    apply_match_events(statuses, MatchResult(0, 0), "x", settings)
    assert statuses[1].available and statuses[1].reason is None


def test_second_yellow_suspends_and_resets_the_count():
    statuses = {1: PlayerStatus()}
    settings = Settings()
    yellow = MatchResult(0, 0, cards=[Card(10, 1, "x", CardType.YELLOW)])

    apply_match_events(statuses, yellow, "x", settings)
    assert statuses[1].available and statuses[1].yellow_cards == 1

    apply_match_events(statuses, yellow, "x", settings)
    assert statuses[1].reason is UnavailableReason.SUSPENDED_YELLOWS
    assert statuses[1].yellow_cards == 0


def test_injury_lasts_as_long_as_the_model_says():
    statuses = {1: PlayerStatus()}
    settings = Settings()

    apply_match_events(statuses, MatchResult(0, 0, injuries=[Injury(10, 1, "x", 2)]), "x", settings)
    assert statuses[1].reason is UnavailableReason.INJURED
    assert statuses[1].matches_remaining == 2

    apply_match_events(statuses, MatchResult(0, 0), "x", settings)
    assert not statuses[1].available
    apply_match_events(statuses, MatchResult(0, 0), "x", settings)
    assert statuses[1].available


def test_events_of_the_other_squad_are_ignored():
    statuses = {1: PlayerStatus()}

    apply_match_events(statuses, MatchResult(0, 0, cards=[Card(10, 1, "rival", CardType.RED)]), "x", Settings())

    assert statuses[1].available


def test_best_lineup_fields_the_strongest_eleven():
    quotas = {Position.GK: 3, Position.DEF: 8, Position.MID: 8, Position.FW: 7}
    squad = [
        Player(len(quotas) * 100 + 10 * index + n, "x", f"{position}{n}", 25, position, 60 + n)
        for index, (position, count) in enumerate(quotas.items())
        for n in range(count)
    ]

    lineup = best_lineup(squad)

    assert len(lineup) == 11
    assert [p.position for p in lineup].count(Position.GK) == 1
    assert next(p for p in lineup if p.position is Position.GK).overall == 62
