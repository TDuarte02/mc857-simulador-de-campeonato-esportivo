import pytest

from collective_attributes_prototype import (
    Player,
    TeamAttributes,
    apply_formation_modifiers,
    calculate_player_scores,
    calculate_team_attributes,
    canonical_position,
    collective_attributes,
    count_formation_sectors,
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


def test_player_from_csv_row_parses_real_dataset_values():
    row = {
        "overall": "93",
        "potential": "93",
        "pace": "85.0",
        "shooting": "92.0",
        "passing": "91.0",
        "dribbling": "95.0",
        "defending": "34.0",
        "physic": "65.0",
        "attacking_heading_accuracy": "70",
        "movement_agility": "91",
        "movement_reactions": "94",
        "movement_balance": "95",
        "power_jumping": "68",
        "power_stamina": "72",
        "mentality_aggression": "44",
        "mentality_penalties": "75",
        "mentality_composure": "96",
        "goalkeeping_reflexes": "8",
    }

    player = Player.from_csv_row("CSV Player", "ST", row)

    assert player.overall == 93
    assert player.potential == 93
    assert player.pace == 85.0
    assert player.shooting == 92.0
    assert player.passing == 91.0
    assert player.dribbling == 95.0
    assert player.defending == 34.0
    assert player.physic == 65.0
    assert player.goalkeeping_reflexes == 8


def test_count_formation_sectors_matches_starting_eleven_433():
    assert count_formation_sectors(starting_eleven) == {
        "goalkeeper": 1,
        "defense": 4,
        "midfield": 3,
        "attack": 3,
    }


def test_apply_formation_modifiers_uses_expected_deltas_for_a_532_shape():
    players = [
        make_test_player("Goalkeeper", "GK"),
        make_test_player("Center Back 1", "CB"),
        make_test_player("Center Back 2", "CB"),
        make_test_player("Full Back 1", "FB"),
        make_test_player("Full Back 2", "FB"),
        make_test_player("Center Back 3", "CB"),
        make_test_player("Midfielder 1", "CM"),
        make_test_player("Midfielder 2", "CM"),
        make_test_player("Midfielder 3", "CM"),
        make_test_player("Striker 1", "ST"),
        make_test_player("Striker 2", "ST"),
    ]

    attributes = TeamAttributes(attack=50.0, defense=50.0, control=50.0)
    modified = apply_formation_modifiers(attributes, players)

    assert modified.attack == pytest.approx(47.0)
    assert modified.defense == pytest.approx(53.0)
    assert modified.control == pytest.approx(50.0)


def test_collective_attributes_433_is_repeatable_for_same_starting_eleven():
    formation_433 = ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W", "W"]

    first = collective_attributes(starting_eleven, formation_433)
    second = collective_attributes(starting_eleven, formation_433)

    assert first == second


def test_calculate_team_attributes_without_formation_config_returns_base_attributes():
    base = calculate_team_attributes(starting_eleven, formation_config=None)
    with_default = calculate_team_attributes(starting_eleven)

    assert base == with_default


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


def test_collective_attributes_rejects_invalid_lineups_and_formations():
    invalid_lineup = starting_eleven[:-1]
    invalid_formation = ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W"]

    with pytest.raises(ValueError, match="exactly 11 starters"):
        collective_attributes(invalid_lineup, ["GK"] * 11)

    with pytest.raises(ValueError, match="must contain 11 slots"):
        collective_attributes(starting_eleven, invalid_formation)

    duplicate_players = starting_eleven[:-1] + [make_test_player("Goalkeeper", "ST")]
    with pytest.raises(ValueError, match="duplicate players"):
        collective_attributes(duplicate_players, ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W", "W"])


def test_calculate_team_attributes_rejects_invalid_goalkeepers_and_positions():
    no_goalkeeper = starting_eleven.copy()
    no_goalkeeper[0] = make_test_player("No Goalkeeper", "CB")

    with pytest.raises(ValueError, match="exatamente um goleiro|exactly one goleiro"):
        calculate_team_attributes(no_goalkeeper)

    with pytest.raises(ValueError, match="Posição desconhecida"):
        canonical_position("INVALID")

    invalid_player = make_test_player("Overrated Striker", "ST", rating=200)
    with pytest.raises(ValueError, match="Pontuação attack inválida"):
        calculate_player_scores(invalid_player)


def test_canonical_position_normalizes_starting_eleven_roles():
    assert canonical_position("RB") == "FB"
    assert canonical_position("LB") == "FB"
    assert canonical_position("CDM") == "DM"
    assert canonical_position("CM") == "CM"
    assert canonical_position("RW") == "W"
    assert canonical_position("LW") == "W"
    assert canonical_position("ST") == "ST"

