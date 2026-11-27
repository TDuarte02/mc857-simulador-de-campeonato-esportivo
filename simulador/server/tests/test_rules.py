from api.config import Settings
from api.domain.models import (
    Card,
    CardType,
    Injury,
    Match,
    MatchResult,
    PlayerStatus,
    Stage,
    UnavailableReason,
)
from api.domain.rules import apply_match_events, compute_standings, qualified_squads

SEED = 7


def played(home: str, away: str, home_goals: int, away_goals: int, cards=()) -> Match:
    result = MatchResult(home_goals, away_goals, cards=list(cards))
    return Match(f"{home}-{away}", "s", Stage.GROUP, 1, home, away, "A", result, played=True)


def order(table) -> list[str]:
    return [row.squad_id for row in table]


def test_standings_count_points_and_goals():
    table = compute_standings("A", ["a", "b", "c"], [played("a", "b", 2, 0), played("b", "c", 1, 1)], SEED)

    assert order(table) == ["a", "c", "b"]
    leader, last = table[0], table[2]
    assert (leader.points, leader.won, leader.goal_difference) == (3, 1, 2)
    assert (last.played, last.drawn, last.lost, last.points) == (2, 1, 1, 1)


def test_standings_ignore_results_not_revealed_yet():
    hidden = played("a", "b", 5, 0)
    hidden.played = False

    assert all(row.played == 0 for row in compute_standings("A", ["a", "b"], [hidden], SEED))


def test_standings_break_ties_by_goal_difference_then_goals():
    by_difference = compute_standings("A", ["a", "b", "c", "d"], [played("a", "c", 3, 0), played("b", "d", 1, 0)], SEED)
    assert order(by_difference)[:2] == ["a", "b"]

    by_goals = compute_standings("A", ["a", "b", "c", "d"], [played("a", "c", 1, 0), played("b", "d", 2, 1)], SEED)
    assert order(by_goals)[:2] == ["b", "a"]


def test_head_to_head_breaks_a_tie_on_points_difference_and_goals():
    # a and b: 3 points, goal difference 0 and 2 goals each; a beat b. c is ahead on difference.
    matches = [played("a", "b", 2, 1), played("c", "a", 1, 0), played("b", "d", 1, 0)]

    tables = [compute_standings("A", ["d", "b", "a", "c"], matches, seed) for seed in range(10)]

    assert all(order(table) == ["c", "a", "b", "d"] for table in tables)


def test_cards_are_counted_but_do_not_break_ties():
    red = Card(40, 1, "a", CardType.RED)
    matches = [played("a", "c", 1, 0, [red, Card(50, 2, "a", CardType.YELLOW)]), played("b", "d", 1, 0)]

    tables = {seed: compute_standings("A", ["a", "b", "c", "d"], matches, seed) for seed in range(20)}

    a = next(row for row in tables[0] if row.squad_id == "a")
    assert (a.red_cards, a.yellow_cards) == (1, 1)
    # a and b are level on everything that counts: the seeded draw orders them, either way round
    assert {order(table)[0] for table in tables.values()} == {"a", "b"}
    assert tables[3] == compute_standings("A", ["a", "b", "c", "d"], matches, 3)


def test_qualified_are_the_top_two_of_each_group_in_group_order():
    groups = {"A": ["a", "b"], "B": ["c", "d"]}
    matches = [played("a", "b", 0, 1), played("c", "d", 2, 0)]
    matches[1].group = "B"

    assert qualified_squads(groups, matches, SEED) == ["b", "a", "c", "d"]


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


def test_two_yellows_in_one_match_are_a_red_and_the_yellow_does_not_accumulate():
    statuses = {1: PlayerStatus(yellow_cards=1)}
    settings = Settings()
    sent_off = MatchResult(
        0, 0, cards=[Card(10, 1, "x", CardType.YELLOW), Card(70, 1, "x", CardType.RED, second_yellow=True)]
    )

    apply_match_events(statuses, sent_off, "x", settings)

    assert statuses[1].reason is UnavailableReason.SUSPENDED_RED
    assert statuses[1].matches_remaining == 1
    assert statuses[1].yellow_cards == 1  # the earlier yellow still counts; this match's does not

    apply_match_events(statuses, MatchResult(0, 0), "x", settings)
    assert statuses[1].available


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
