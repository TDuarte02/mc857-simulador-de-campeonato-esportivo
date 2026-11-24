import csv
import os
import subprocess
import sys
from dataclasses import fields
from pathlib import Path

import pytest

from python_prototype.collective_attributes import (
    POSITION_SECTORS,
    Player,
    canonical_position,
    calculate_team_attributes,
    formation_distribution,
)
from python_prototype.tournament import (
    DEFAULT_FORMATION,
    DEFAULT_NATIONS,
    SetupError,
    SquadMember,
    TournamentConfig,
    build_default_lineup,
    build_national_team,
    build_squad,
    derive_seed,
    draw_groups,
    load_national_teams,
    read_players_csv,
    setup_tournament,
    synthetic_team,
    synthetic_teams,
    uniform_player,
)

ATTRS = [f.name for f in fields(Player) if f.name not in ("name", "pos")]
COLUMNS = ["short_name", "long_name", "player_positions", "nationality_name", *ATTRS]
LINE_ATTRS = ("pace", "shooting", "passing", "dribbling", "defending", "physic")


def member(name, positions, overall=70, **overrides):
    positions = tuple(positions)
    player = uniform_player(name, positions[0], overall)
    if overrides:
        from dataclasses import replace
        player = replace(player, overall=overall, **overrides)
    return SquadMember(player, positions)


def full_roster(prefix="N", base=80):
    """3 goleiros + 20 de linha cobrindo todas as posições do 4-3-3."""
    gks = [member(f"{prefix}GK{i}", ["GK"], base - i) for i in range(3)]
    layout = ["RB", "CB", "CB", "LB", "CB", "RB", "CM", "CDM", "CAM", "CM",
              "ST", "LW", "RW", "CF", "ST", "LW", "RW", "CM", "CB", "LB"]
    outfield = [member(f"{prefix}{i:02d}", [p], base - 5 - i) for i, p in enumerate(layout)]
    return gks + outfield


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def csv_row(name, nation, positions, overall=70, **overrides):
    row = {c: str(overall) for c in ATTRS}
    row.update(short_name=name, long_name=name, player_positions=positions, nationality_name=nation)
    row.update(overrides)
    return row


# ------------------------------------------------------------
# Semente e configuração
# ------------------------------------------------------------

def test_derive_seed_is_deterministic_and_label_sensitive():
    assert derive_seed(1, "a", 2) == derive_seed(1, "a", 2)
    assert derive_seed(1, "a") != derive_seed(2, "a")
    assert derive_seed(1, "a", "b") != derive_seed(1, "ab")
    assert derive_seed(1, "draw", 1) != derive_seed(1, "draw", 2)


def test_derive_seed_is_identical_across_processes():
    root = Path(__file__).resolve().parents[2]
    code = "from python_prototype.tournament import derive_seed; print(derive_seed(2026, 'draw', 1))"
    outputs = {
        subprocess.run(
            [sys.executable, "-c", code], cwd=root, capture_output=True, text=True, check=True,
            env={**os.environ, "PYTHONHASHSEED": hash_seed},
        ).stdout.strip()
        for hash_seed in ("1", "2", "random")
    }
    assert outputs == {str(derive_seed(2026, "draw", 1))}


@pytest.mark.parametrize("bad", ["x", 1.5, True, None])
def test_derive_seed_rejects_non_int_seed(bad):
    with pytest.raises(ValueError):
        derive_seed(bad, "x")


def test_default_config_has_16_nations_and_valid_formation():
    config = TournamentConfig()
    assert len(set(config.nations)) == 16
    assert config.squad_size == 23
    assert formation_distribution(config.formation) == {"GK": 1, "DEF": 4, "MID": 3, "FW": 3}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"nations": DEFAULT_NATIONS[:15]},
        {"nations": DEFAULT_NATIONS[:15] + (DEFAULT_NATIONS[0],)},
        {"formation": DEFAULT_FORMATION[:10]},
        {"formation": ("GK", "GK") + DEFAULT_FORMATION[2:]},
        {"squad_goalkeepers": 0},
        {"squad_size": 12},
        {"seed": "x"},
    ],
)
def test_invalid_config_is_rejected(kwargs):
    with pytest.raises(ValueError):
        TournamentConfig(**kwargs)


# ------------------------------------------------------------
# Dataset
# ------------------------------------------------------------

def test_csv_filters_by_nation_and_reports_discards(tmp_path):
    path = tmp_path / "players.csv"
    write_csv(path, [
        csv_row("Ok One", "Brazil", "ST, LW", 80),
        csv_row("Odd Pos", "Brazil", "XYZ, CB", 75),            # XYZ ignorada
        csv_row("No Pos", "Brazil", "XYZ", 75),                 # descartado
        csv_row("Empty Pace", "Brazil", "CM", 75, pace=""),     # linha vazia: descartado
        csv_row("Bad Value", "Brazil", "CM", 75, shooting="x"), # inválido: descartado
        csv_row("Elsewhere", "Germany", "ST", 90),              # filtrado
    ])

    members, report = read_players_csv(path, ["Brazil", "Peru"])

    assert [m.player.name for m in members["Brazil"]] == ["Ok One", "Odd Pos"]
    assert members["Brazil"][0].positions == ("ST", "LW")
    assert members["Brazil"][1].positions == ("CB",)
    assert members["Peru"] == []
    assert report.rows_read == 5
    assert {d.name for d in report.discarded} == {"No Pos", "Empty Pace", "Bad Value"}
    assert all(d.line > 1 and d.nation == "Brazil" and d.reason for d in report.discarded)


def test_goalkeeper_with_empty_line_attributes_gets_zeros(tmp_path):
    path = tmp_path / "players.csv"
    write_csv(path, [csv_row("Keeper", "Brazil", "GK", 85, **{a: "" for a in LINE_ATTRS})])

    members, report = read_players_csv(path, ["Brazil"])

    player = members["Brazil"][0].player
    assert all(getattr(player, a) == 0 for a in LINE_ATTRS)
    assert members["Brazil"][0].is_goalkeeper
    assert report.discarded == ()


def test_csv_missing_columns_is_an_explicit_error(tmp_path):
    path = tmp_path / "players.csv"
    path.write_text("short_name,nationality_name\nA,Brazil\n", encoding="utf-8")

    with pytest.raises(SetupError, match="colunas"):
        read_players_csv(path, ["Brazil"])


def test_load_national_teams_from_csv_and_nation_without_players(tmp_path):
    nations = DEFAULT_NATIONS
    rows = []
    for nation in nations[:-1]:
        for m in full_roster(nation[:3], 80):
            rows.append(csv_row(m.player.name, nation, m.positions[0], m.player.overall))
    path = tmp_path / "players.csv"
    write_csv(path, rows)

    with pytest.raises(SetupError, match=nations[-1]):
        load_national_teams(TournamentConfig(dataset_path=path))

    last = nations[-1]
    write_csv(path, rows + [
        csv_row(m.player.name, last, m.positions[0], m.player.overall)
        for m in full_roster(last[:3], 80)
    ])
    teams, report = load_national_teams(TournamentConfig(dataset_path=path))
    assert list(teams) == list(nations)
    assert report.discarded == ()


# ------------------------------------------------------------
# Elenco
# ------------------------------------------------------------

def test_squad_has_3_goalkeepers_and_20_best_outfield_players():
    roster = full_roster() + [member(f"Extra{i}", ["CB"], 10 + i) for i in range(5)] \
        + [member(f"GKExtra{i}", ["GK"], 5) for i in range(2)]

    squad = build_squad(roster, TournamentConfig())

    assert len(squad) == 23
    assert sum(m.is_goalkeeper for m in squad) == 3
    assert not any(m.player.name.startswith(("Extra", "GKExtra")) for m in squad)


def test_squad_tie_break_is_alphabetical_and_names_are_unique():
    roster = [member("Zed", ["GK"], 70), member("Amy", ["GK"], 70)]
    roster += [member("Dup", ["CB"], 60) for _ in range(3)]
    roster += [member(f"P{i}", ["CM"], 50) for i in range(17)]

    squad = build_squad(roster, TournamentConfig())

    assert [m.player.name for m in squad[:2]] == ["Amy", "Zed"]
    names = [m.player.name for m in squad]
    assert len(set(names)) == len(names)
    assert {"Dup", "Dup (2)", "Dup (3)"} <= set(names)


# ------------------------------------------------------------
# Escalação padrão
# ------------------------------------------------------------

def test_default_lineup_is_valid_deterministic_and_keeps_originals():
    squad = build_squad(full_roster(), TournamentConfig())
    before = [m.player for m in squad]

    first = build_default_lineup("N", squad, DEFAULT_FORMATION)
    second = build_default_lineup("N", squad, DEFAULT_FORMATION)

    assert first == second
    assert len(first) == 11 and len({p.name for p in first}) == 11
    calculate_team_attributes(first, DEFAULT_FORMATION)
    assert [m.player for m in squad] == before


def test_goalkeeper_is_only_in_goal_and_best_goalkeeper_plays():
    squad = build_squad(full_roster(), TournamentConfig())

    lineup = build_default_lineup("N", squad, DEFAULT_FORMATION)

    assert canonical_position(lineup[0].pos) == "GK" and lineup[0].name == "NGK0"
    assert all(canonical_position(p.pos) != "GK" for p in lineup[1:])


def test_slots_are_filled_with_best_matching_player():
    squad = build_squad(full_roster(), TournamentConfig())

    lineup = build_default_lineup("N", squad, DEFAULT_FORMATION)

    # Slots 2 e 3 são CB: os melhores CB são os de menor índice (N01, N02).
    assert [lineup[2].name, lineup[3].name] == ["N01", "N02"]
    assert lineup[8].name == "N10"        # ST: melhor ST/CF
    assert lineup[8].pos == "ST"


def test_sector_fallback_recreates_player_with_slot_position():
    roster = [member("GK", ["GK"], 70)]
    roster += [member(f"D{i}", ["CB"], 70 - i) for i in range(4)]
    roster += [member(f"M{i}", ["CM"], 70 - i) for i in range(3)]
    roster += [member(f"F{i}", ["ST"], 70 - i) for i in range(3)]   # sem nenhum W
    squad = tuple(roster)

    lineup = build_default_lineup("N", squad, DEFAULT_FORMATION)

    assert [p.pos for p in lineup[-3:]] == ["ST", "W", "W"]
    assert {p.name for p in lineup[-3:]} == {"F0", "F1", "F2"}
    assert squad[-1].player.pos == "ST"                      # original intocado
    assert formation_distribution([p.pos for p in lineup]) == formation_distribution(DEFAULT_FORMATION)


def test_missing_goalkeeper_is_never_improvised():
    squad = tuple(m for m in full_roster() if not m.is_goalkeeper)

    with pytest.raises(SetupError, match="Atlantis.*goleiro"):
        build_default_lineup("Atlantis", squad, DEFAULT_FORMATION)


def test_missing_sector_gives_explicit_error_with_nation():
    squad = tuple(m for m in full_roster() if "FW" not in m.sectors)

    with pytest.raises(SetupError, match="Atlantis.*FW"):
        build_default_lineup("Atlantis", squad, DEFAULT_FORMATION)


def test_empty_nation_gives_explicit_error():
    with pytest.raises(SetupError, match="Atlantis"):
        build_national_team("Atlantis", [], TournamentConfig())


# ------------------------------------------------------------
# Seleções sintéticas
# ------------------------------------------------------------

def test_synthetic_team_is_valid_and_uniform():
    team = synthetic_team("Synth", 70)

    assert len(team.squad) == 23 and len(team.lineup) == 11
    assert team.attributes.attack == pytest.approx(team.attributes.attack)
    base = calculate_team_attributes(team.lineup, team.formation, formation_config=None)
    assert (base.attack, base.defense, base.control) == pytest.approx((70, 70, 70))


def test_synthetic_teams_cover_all_nations_with_increasing_strength():
    teams = synthetic_teams()

    assert [t.name for t in teams] == list(DEFAULT_NATIONS)
    strengths = [t.strength for t in teams]
    assert strengths == sorted(strengths) and len(set(strengths)) == 16
    with pytest.raises(ValueError):
        synthetic_teams(ratings=[70] * 15)


# ------------------------------------------------------------
# Sorteio
# ------------------------------------------------------------

def test_draw_gives_each_group_one_team_per_pot():
    draw = draw_groups(synthetic_teams(), seed=1)

    assert [g.name for g in draw.groups] == ["A", "B", "C", "D"]
    assert all(len(pot) == 4 for pot in draw.pots)
    for group in draw.groups:
        assert len(group.teams) == 4
        for position, team in enumerate(group.teams, start=1):
            assert team in draw.pots[position - 1]
            assert group.position_of(team.name) == position
    names = [t.name for g in draw.groups for t in g.teams]
    assert len(names) == 16 and len(set(names)) == 16


def test_pots_are_ordered_by_strength_with_name_tie_break():
    teams = synthetic_teams(ratings=[70] * 16)    # todos empatados: ordem alfabética

    draw = draw_groups(teams, seed=0)

    flat = [t.name for pot in draw.pots for t in pot]
    assert flat == sorted(DEFAULT_NATIONS)

    strong = synthetic_teams()
    pots = draw_groups(strong, seed=0).pots
    assert min(t.strength for t in pots[0]) > max(t.strength for t in pots[1])


def test_draw_is_reproducible_and_respects_pots_for_any_seed():
    teams = synthetic_teams()

    assert draw_groups(teams, 7) == draw_groups(teams, 7)
    layouts = set()
    for seed in range(20):
        draw = draw_groups(teams, seed)
        layouts.add(tuple(tuple(t.name for t in g.teams) for g in draw.groups))
        for group in draw.groups:
            assert all(t in draw.pots[i] for i, t in enumerate(group.teams))
    assert len(layouts) > 1


def test_draw_rejects_wrong_number_of_teams():
    with pytest.raises(ValueError):
        draw_groups(synthetic_teams()[:15], seed=1)


def test_setup_tournament_with_synthetic_teams_uses_config_seed():
    config = TournamentConfig(seed=5)
    teams = synthetic_teams(config)

    setup = setup_tournament(config, teams)

    assert setup.report is None
    assert setup.draw == draw_groups(teams, 5)
    assert [t.name for t in setup.teams] == list(config.nations)
