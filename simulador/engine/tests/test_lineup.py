import pytest

from copa_engine.collective_attributes import (
    calculate_team_attributes,
    canonical_position,
    formation_distribution,
    validate_lineup_matches_formation,
)
from copa_engine.lineup import (
    DEFAULT_FORMATION,
    FORMATIONS,
    LineupDoesNotFit,
    SetupError,
    SquadMember,
    assign_slots,
    covers_sectors,
    default_lineup,
)
from copa_engine.penalties import goalkeeper_of
from tests.helpers import make_player, synthetic_team


def member(name, *positions, rating=70, **overrides):
    if positions[0] != "GK":
        overrides.setdefault("goalkeeping_reflexes", 10)
    return SquadMember(make_player(name, positions[0], rating, **overrides), tuple(positions))


def xi_442():
    """1 GK, 4 DEF, 4 MID, 2 FW, cada um na sua posição exata."""
    return [
        member("gk", "GK"),
        member("rb", "RB"), member("cb1", "CB"), member("cb2", "CB"), member("lb", "LB"),
        member("cm1", "CM"), member("cdm", "CDM"), member("cam", "CAM"), member("cm2", "CM"),
        member("st", "ST"), member("lw", "LW"),
    ]


# ------------------------------------------------------------
# Escalação padrão
# ------------------------------------------------------------

def full_roster(prefix="N", base=80):
    """3 goleiros + 20 de linha cobrindo todas as posições do 4-3-3."""
    gks = [member(f"{prefix}GK{i}", "GK", rating=base - i) for i in range(3)]
    layout = ["RB", "CB", "CB", "LB", "CB", "RB", "CM", "CDM", "CAM", "CM",
              "ST", "LW", "RW", "CF", "ST", "LW", "RW", "CM", "CB", "LB"]
    outfield = [member(f"{prefix}{i:02d}", p, rating=base - 5 - i) for i, p in enumerate(layout)]
    return tuple(gks + outfield)


def test_default_lineup_is_valid_deterministic_and_keeps_originals():
    squad = full_roster()
    before = [m.player for m in squad]

    first = default_lineup("N", squad, DEFAULT_FORMATION)
    second = default_lineup("N", squad)

    assert first == second
    assert len(first) == 11 and len({p.name for p in first}) == 11
    calculate_team_attributes(first, DEFAULT_FORMATION)
    assert [m.player for m in squad] == before


def test_goalkeeper_is_only_in_goal_and_best_goalkeeper_plays():
    lineup = default_lineup("N", full_roster())

    assert canonical_position(lineup[0].pos) == "GK" and lineup[0].name == "NGK0"
    assert all(canonical_position(p.pos) != "GK" for p in lineup[1:])


def test_slots_are_filled_with_best_matching_player():
    lineup = default_lineup("N", full_roster())

    # Slots 2 e 3 são CB: os melhores CB são os de menor índice (N01, N02).
    assert [lineup[2].name, lineup[3].name] == ["N01", "N02"]
    assert lineup[8].name == "N10"        # ST: melhor ST/CF
    assert lineup[8].pos == "ST"


def test_sector_fallback_recreates_player_with_slot_position():
    roster = [member("GK", "GK")]
    roster += [member(f"D{i}", "CB", rating=70 - i) for i in range(4)]
    roster += [member(f"M{i}", "CM", rating=70 - i) for i in range(3)]
    roster += [member(f"F{i}", "ST", rating=70 - i) for i in range(3)]   # sem nenhum W
    squad = tuple(roster)

    lineup = default_lineup("N", squad)

    assert [p.pos for p in lineup[-3:]] == ["ST", "W", "W"]
    assert {p.name for p in lineup[-3:]} == {"F0", "F1", "F2"}
    assert squad[-1].player.pos == "ST"                      # original intocado
    assert formation_distribution([p.pos for p in lineup]) == formation_distribution(DEFAULT_FORMATION)


def test_missing_goalkeeper_is_never_improvised():
    squad = tuple(m for m in full_roster() if not m.is_goalkeeper)

    with pytest.raises(SetupError, match="Atlantis.*goleiro"):
        default_lineup("Atlantis", squad)


def test_missing_sector_gives_explicit_error_with_nation():
    squad = tuple(m for m in full_roster() if "FW" not in m.sectors)

    with pytest.raises(SetupError, match="Atlantis.*FW"):
        default_lineup("Atlantis", squad)


def test_synthetic_team_is_valid_and_uniform():
    team = synthetic_team("Synth", 70)

    assert len(team.squad) == 23 and len(team.lineup) == 11
    base = calculate_team_attributes(team.lineup, DEFAULT_FORMATION, formation_config=None)
    assert (base.attack, base.defense, base.control) == pytest.approx((70, 70, 70))
    assert synthetic_team("Synth", 70, FORMATIONS["4-4-2"], goalkeepers=2, outfield=18).squad[2].positions == ("FB",)


def test_covers_sectors_needs_4_defenders_5_midfielders_and_3_forwards():
    outfield = [m for m in full_roster() if not m.is_goalkeeper]

    assert covers_sectors(outfield)
    assert not covers_sectors([m for m in outfield if "MID" not in m.sectors] + outfield[6:8])


# ------------------------------------------------------------
# Formações e encaixe nos slots
# ------------------------------------------------------------

@pytest.mark.parametrize(
    "name, counts",
    [
        ("4-4-2", {"GK": 1, "DEF": 4, "MID": 4, "FW": 2}),
        ("4-3-3", {"GK": 1, "DEF": 4, "MID": 3, "FW": 3}),
        ("3-5-2", {"GK": 1, "DEF": 3, "MID": 5, "FW": 2}),
        ("4-2-3-1", {"GK": 1, "DEF": 4, "MID": 5, "FW": 1}),
    ],
)
def test_formations_have_the_apps_sector_counts(name, counts):
    assert formation_distribution(FORMATIONS[name]) == counts


def test_the_users_4_3_3_is_the_machines_formation():
    assert FORMATIONS["4-3-3"] == DEFAULT_FORMATION


def test_exact_positions_are_preferred_and_players_come_in_slot_order():
    lineup = assign_slots(xi_442(), FORMATIONS["4-4-2"])

    names = [p.name for p in lineup]
    assert names[0] == "gk"
    assert {names[1], names[4]} == {"rb", "lb"} and {names[2], names[3]} == {"cb1", "cb2"}
    assert set(names[5:9]) == {"cm1", "cdm", "cam", "cm2"} and set(names[9:]) == {"st", "lw"}
    by_name = {p.name: p for p in lineup}
    assert (by_name["rb"].pos, by_name["cb1"].pos, by_name["st"].pos) == ("RB", "CB", "ST")
    # fora da posição exata, o jogador assume o slot
    assert (by_name["cdm"].pos, by_name["cam"].pos, by_name["lw"].pos) == ("CM", "CM", "ST")
    validate_lineup_matches_formation(lineup, FORMATIONS["4-4-2"])
    calculate_team_attributes(lineup, FORMATIONS["4-4-2"])


def test_matching_places_players_where_the_greedy_default_lineup_fails():
    # "flex" (CB/CM) é o melhor: o guloso o põe na zaga, sobra um zagueiro puro
    # e falta um atacante. O emparelhamento o leva para o meio.
    xi = [
        member("gk", "GK"),
        member("flex", "CB", "CM", rating=90),
        member("d1", "CB"), member("d2", "CB"), member("d3", "RB"), member("d4", "LB"),
        member("m1", "CM"), member("m2", "CM"), member("m3", "CM"),
        member("hybrid", "CM", "ST"), member("st", "ST"),
    ]
    with pytest.raises(SetupError):
        default_lineup("X", xi, FORMATIONS["4-4-2"])

    lineup = assign_slots(xi, FORMATIONS["4-4-2"])

    by_name = {p.name: p for p in lineup}
    assert canonical_position(by_name["flex"].pos) == "CM"
    assert canonical_position(by_name["hybrid"].pos) == "ST"
    validate_lineup_matches_formation(lineup, FORMATIONS["4-4-2"])


def test_an_impossible_lineup_names_the_players_that_do_not_fit():
    xi = xi_442()
    xi[9] = member("cb3", "CB")  # 5 defensores e 1 atacante num 4-4-2

    with pytest.raises(LineupDoesNotFit) as error:
        assign_slots(xi, FORMATIONS["4-4-2"])

    assert len(error.value.players) == 1
    assert error.value.players[0] in {"rb", "cb1", "cb2", "lb", "cb3"}


def test_two_goalkeepers_do_not_fit():
    xi = xi_442()
    xi[10] = member("gk2", "GK")

    with pytest.raises(LineupDoesNotFit) as error:
        assign_slots(xi, FORMATIONS["4-4-2"])
    assert error.value.players == ("gk2",)


def test_without_a_goalkeeper_the_best_fitting_reflexes_go_in_goal():
    # 4 DEF, 5 MID, 2 FW, ninguém no gol. O atacante tem os melhores reflexos,
    # mas tirá-lo deixa um 4-4-2 sem o 2º atacante; o meia "m5" serve.
    xi = [
        member("d1", "CB"), member("d2", "CB"), member("d3", "RB"), member("d4", "LB"),
        member("m1", "CM"), member("m2", "CM"), member("m3", "CM"), member("m4", "CM"),
        member("m5", "CAM", goalkeeping_reflexes=40),
        member("f1", "ST", goalkeeping_reflexes=60), member("f2", "ST"),
    ]

    lineup = assign_slots(xi, FORMATIONS["4-4-2"])

    keeper = goalkeeper_of(lineup)
    assert (keeper.name, keeper.pos) == ("m5", "GK")
    assert lineup[0] is keeper
    validate_lineup_matches_formation(lineup, FORMATIONS["4-4-2"])


def test_without_a_goalkeeper_the_highest_reflexes_win_when_they_fit():
    xi = [m for m in xi_442() if m.player.name != "gk"] + [member("extra", "CM", goalkeeping_reflexes=80)]

    lineup = assign_slots(xi, FORMATIONS["4-4-2"])

    assert goalkeeper_of(lineup).name == "extra"


def test_without_a_goalkeeper_and_no_candidate_it_does_not_fit():
    xi = [member(f"d{i}", "CB") for i in range(11)]

    with pytest.raises(LineupDoesNotFit):
        assign_slots(xi, FORMATIONS["4-4-2"])


@pytest.mark.parametrize("name", sorted(FORMATIONS))
def test_every_formation_accepts_a_squad_shaped_like_it(name):
    by_sector = {"GK": "GK", "DEF": "CB", "MID": "CM", "FW": "ST"}
    from copa_engine.collective_attributes import POSITION_SECTORS

    xi = [
        member(f"p{i}", by_sector[POSITION_SECTORS[canonical_position(slot)]])
        for i, slot in enumerate(FORMATIONS[name])
    ]

    lineup = assign_slots(xi, FORMATIONS[name])

    validate_lineup_matches_formation(lineup, FORMATIONS[name])
