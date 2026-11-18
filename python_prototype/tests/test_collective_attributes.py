import pytest
import math
from dataclasses import asdict

from python_prototype.collective_attributes import (
    Player,
    TeamAttributes,
    apply_formation_modifiers,
    calculate_player_scores,
    calculate_team_attributes,
    canonical_position,
    calculate_team_attributes,
    formation_distribution,
    POSITION_ALIASES, POSITION_WEIGHTS, POSITION_SECTORS, SECTORS,

)

from python_prototype.tests.helpers import (
    FORMATION_433,
    FORMATION_442,
    POSITIONS_442,
    POSITIONS_532,
    make_lineup,
    make_player,
)

starting_eleven = [
    make_player("Goalkeeper", "GK"),
    make_player("Right Back", "RB"),
    make_player("Center Back 1", "CB"),
    make_player("Center Back 2", "CB"),
    make_player("Left Back", "LB"),
    make_player("Defensive Midfielder", "CDM"),
    make_player("Central Midfielder 1", "CM"),
    make_player("Central Midfielder 2", "CM"),
    make_player("Right Winger", "RW"),
    make_player("Striker", "ST"),
    make_player("Left Winger", "LW"),
]

def make_lineup(positions, rating: int = 70):
    return [make_player(f"Player {i}", pos, rating) for i, pos in enumerate(positions)]

def squad(prefix: str, rating: int, positions=POSITIONS_442):
    return [make_player(f"{prefix}{i}", pos, rating) for i, pos in enumerate(positions)]

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


def test_formation_distribution_works_on_player_positions():
    positions = [player.pos for player in starting_eleven]

    assert formation_distribution(positions) == {"GK": 1, "DEF": 4, "MID": 3, "FW": 3}


def test_apply_formation_modifiers_uses_expected_deltas_for_a_532_shape():
    players = [
        make_player("Goalkeeper", "GK"),
        make_player("Center Back 1", "CB"),
        make_player("Center Back 2", "CB"),
        make_player("Full Back 1", "FB"),
        make_player("Full Back 2", "FB"),
        make_player("Center Back 3", "CB"),
        make_player("Midfielder 1", "CM"),
        make_player("Midfielder 2", "CM"),
        make_player("Midfielder 3", "CM"),
        make_player("Striker 1", "ST"),
        make_player("Striker 2", "ST"),
    ]

    attributes = TeamAttributes(attack=50.0, defense=50.0, control=50.0)
    modified = apply_formation_modifiers(attributes, [p.pos for p in players])

    assert modified.attack == pytest.approx(47.0)
    assert modified.defense == pytest.approx(53.0)
    assert modified.control == pytest.approx(50.0)


def test_calculate_team_attributes_433_is_repeatable_for_same_starting_eleven():
    formation_433 = ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W", "W"]

    first = calculate_team_attributes(starting_eleven, formation_433)
    second = calculate_team_attributes(starting_eleven, formation_433)

    assert first == second


def test_formation_config_none_returns_base_attributes_without_modifiers():
    lineup = make_lineup(POSITIONS_532)

    base = calculate_team_attributes(lineup, formation_config=None)
    modified = calculate_team_attributes(lineup)

    assert base.attack == pytest.approx(70.0)
    assert modified.attack == pytest.approx(67.0)    # DEF +1, FW -1
    assert modified.defense == pytest.approx(73.0)
    assert modified.control == pytest.approx(70.0)


def test_calculate_team_attributes_changes_when_formation_changes():
    lineup_442 = make_lineup(POSITIONS_442)

    attrs_433 = calculate_team_attributes(starting_eleven, FORMATION_433)
    attrs_442 = calculate_team_attributes(lineup_442, FORMATION_442)

    assert attrs_433.attack > attrs_442.attack
    assert attrs_442.defense > attrs_433.defense
    assert attrs_442.control > attrs_433.control


def test_calculate_team_attributes_does_not_mutate_starting_eleven():
    original = starting_eleven.copy()
    formation = ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W", "W"]

    calculate_team_attributes(starting_eleven, formation)

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


def test_calculate_team_attributes_rejects_invalid_lineups_and_formations():
    invalid_lineup = starting_eleven[:-1]
    invalid_formation = ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W"]

    with pytest.raises(ValueError, match="exatamente 11 titulares"):
        calculate_team_attributes(invalid_lineup, ["GK"] * 11)

    with pytest.raises(ValueError, match="exatamente 11 slots"):
        calculate_team_attributes(starting_eleven, invalid_formation)

    duplicate_players = starting_eleven[:-1] + [make_player("Goalkeeper", "ST")]
    with pytest.raises(ValueError, match="jogadores duplicados"):
        calculate_team_attributes(duplicate_players, ["GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "ST", "W", "W"])


def test_calculate_team_attributes_rejects_invalid_goalkeepers_and_positions():
    no_goalkeeper = starting_eleven.copy()
    no_goalkeeper[0] = make_player("No Goalkeeper", "CB")

    with pytest.raises(ValueError, match="exatamente um goleiro"):
        calculate_team_attributes(no_goalkeeper)

    with pytest.raises(ValueError, match="Posição desconhecida"):
        canonical_position("INVALID")

    with pytest.raises(ValueError, match="fora da escala"):
        make_player("Overrated Striker", "ST", rating=200)


def test_canonical_position_normalizes_starting_eleven_roles():
    assert canonical_position("RB") == "FB"
    assert canonical_position("LB") == "FB"
    assert canonical_position("CDM") == "DM"
    assert canonical_position("CM") == "CM"
    assert canonical_position("RW") == "W"
    assert canonical_position("LW") == "W"
    assert canonical_position("ST") == "ST"

def test_lineup_must_match_formation_sectors():
    # starting_eleven é 4-3-3; a formação 4-4-2 tem um meio-campista a mais
    with pytest.raises(ValueError, match="não corresponde à formação"):
        calculate_team_attributes(starting_eleven, FORMATION_442)


def test_mismatch_message_reports_both_distributions():
    with pytest.raises(ValueError) as exc:
        calculate_team_attributes(starting_eleven, FORMATION_442)

    message = str(exc.value)
    assert "jogadores GK=1 DEF=4 MID=3 FW=3" in message
    assert "formação GK=1 DEF=4 MID=4 FW=2" in message


def test_matching_non_433_lineup_applies_formation_modifiers():
    lineup = make_lineup(POSITIONS_442)

    attrs = calculate_team_attributes(lineup, FORMATION_442)

    # Base uniforme 70; deltas 4-4-2 vs 4-3-3: MID +1, FW -1.
    assert attrs.attack == pytest.approx(70 + 0.5 - 2.0)
    assert attrs.defense == pytest.approx(70 - 0.5 + 1.0)
    assert attrs.control == pytest.approx(70 + 2.0 + 0.5)


def test_validation_is_by_sector_not_by_slot():
    # Mesmos setores do 4-3-3, mas com slots diferentes dentro de cada setor.
    formation = ["GK", "CB", "CB", "CB", "CB", "DM", "AM", "CM", "ST", "ST", "W"]

    attrs = calculate_team_attributes(starting_eleven, formation)

    assert attrs == calculate_team_attributes(starting_eleven, FORMATION_433)


@pytest.mark.parametrize("gk_slots", [0, 2])
def test_formation_must_have_exactly_one_goalkeeper(gk_slots):
    formation = ["CB"] * 4 + ["CM"] * 3 + ["ST"] * 3   # 10 slots de linha
    formation = formation + ["CB"] if gk_slots == 0 else ["GK", "GK"] + formation[1:]

    with pytest.raises(ValueError, match="formação deve conter exatamente um goleiro"):
        calculate_team_attributes(starting_eleven, formation)


def test_lineup_with_two_goalkeepers_is_rejected():
    positions = ["GK", "RB", "CB", "CB", "LB", "CM", "CM", "GK", "RW", "ST", "LW"]

    with pytest.raises(ValueError, match="não corresponde à formação"):
        calculate_team_attributes(make_lineup(positions), FORMATION_433)


def test_size_and_duplicate_checks_run_before_sector_validation():
    # Formação incoerente E lineup curta: a mensagem de tamanho vence.
    with pytest.raises(ValueError, match="exatamente 11 titulares"):
        calculate_team_attributes(starting_eleven[:-1], FORMATION_442)

def test_formation_is_derived_from_players_when_omitted():
    lineup = make_lineup(POSITIONS_442)

    assert calculate_team_attributes(lineup) == calculate_team_attributes(
        lineup, FORMATION_442
    )



def test_calculate_team_attributes_rejects_duplicate_players():
    duplicated = starting_eleven[:-1] + [make_player("Goalkeeper", "ST")]

    with pytest.raises(ValueError, match="jogadores duplicados"):
        calculate_team_attributes(duplicated)


def test_formation_modifiers_are_clamped_to_scale_limits():
    formation = [p.pos for p in make_lineup(POSITIONS_532)]   # attack -3, defense +3
    near_limits = TeamAttributes(attack=1.0, defense=99.0, control=50.0)

    result = apply_formation_modifiers(near_limits, formation)

    assert result.attack == 0.0
    assert result.defense == 100.0
    assert result.control == pytest.approx(50.0)


def test_position_tables_are_consistent():
    assert set(POSITION_ALIASES.values()) == set(POSITION_WEIGHTS) == set(POSITION_SECTORS)
    assert set(POSITION_SECTORS.values()) == set(SECTORS)

