import pytest

from collective_attributes_prototype import (
    Player,
    calculate_player_scores,
    calculate_team_attributes,
    canonical_position,
    collective_attributes,
    formation_distribution,
)


def make_test_player(name: str, pos: str, rating: int = 70) -> Player:
    return Player(
        name=name,
        pos=pos,
        overall=rating,
        potential=rating,
        pace=rating,
        shooting=rating,
        passing=rating,
        dribbling=rating,
        defending=rating,
        physic=rating,
        attacking_heading_accuracy=rating,
        movement_agility=rating,
        movement_reactions=rating,
        movement_balance=rating,
        power_jumping=rating,
        power_stamina=rating,
        mentality_aggression=rating,
        mentality_penalties=rating,
        mentality_composure=rating,
        goalkeeping_reflexes=rating,
    )


starting_eleven = [
    make_test_player("Goalkeeper", "GK"),
    make_test_player("Right Back", "RB"),
    make_test_player("Center Back 1", "CB"),
    make_test_player("Center Back 2", "CB"),
    make_test_player("Left Back", "LB"),
    make_test_player("Defensive Midfielder", "CDM"),
    make_test_player("Central Midfielder 1", "CM"),
    make_test_player("Central Midfielder 2", "CM"),
    make_test_player("Right Winger", "RW"),
    make_test_player("Striker", "ST"),
    make_test_player("Left Winger", "LW"),
]


def test_collective_attributes_433_is_repeatable_for_same_starting_eleven():
    formation_433 = ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W", "W"]

    first = collective_attributes(starting_eleven, formation_433)
    second = collective_attributes(starting_eleven, formation_433)

    assert first == second


def test_collective_attributes_changes_when_formation_changes():
    formation_433 = ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W", "W"]
    formation_442 = ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "CM", "ST", "ST"]

    attrs_433 = collective_attributes(starting_eleven, formation_433)
    attrs_442 = collective_attributes(starting_eleven, formation_442)

    assert attrs_433["attack"] > attrs_442["attack"]
    assert attrs_442["defense"] > attrs_433["defense"]
    assert attrs_442["control"] > attrs_433["control"]


def test_collective_attributes_does_not_mutate_starting_eleven():
    original = starting_eleven.copy()
    formation = ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W", "W"]

    collective_attributes(starting_eleven, formation)

    assert starting_eleven == original


def test_formation_distribution_matches_starting_eleven_433_shape():
    formation_433 = ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W", "W"]

    assert formation_distribution(formation_433) == {
        "GK": 1,
        "DEF": 4,
        "MID": 3,
        "FW": 3,
    }


def test_calculate_team_attributes_accepts_starting_eleven():
    attributes = calculate_team_attributes(starting_eleven)

    assert 0.0 <= attributes.attack <= 100.0
    assert 0.0 <= attributes.defense <= 100.0
    assert 0.0 <= attributes.control <= 100.0


def test_calculate_player_scores_uses_real_player_attributes_for_starting_eleven():
    scores = calculate_player_scores(starting_eleven[0])

    assert scores.attack == pytest.approx(70.0)
    assert scores.defense == pytest.approx(70.0)
    assert scores.control == pytest.approx(70.0)


def test_canonical_position_normalizes_starting_eleven_roles():
    assert canonical_position("RB") == "FB"
    assert canonical_position("LB") == "FB"
    assert canonical_position("CDM") == "DM"
    assert canonical_position("CM") == "CM"
    assert canonical_position("RW") == "W"
    assert canonical_position("LW") == "W"
    assert canonical_position("ST") == "ST"

