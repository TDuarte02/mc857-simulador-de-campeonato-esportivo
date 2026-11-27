"""The engine as the server's simulator: the adapter, slot assignment, determinism and the API around it."""

import csv
import random
from dataclasses import replace
from pathlib import Path

import pytest
from copa_engine.collective_attributes import POSITION_SECTORS
from copa_engine.collective_attributes import canonical_position as engine_canonical
from copa_engine.lineup import FORMATIONS

from api.container import build_container
from api.domain.engine_data import sector_of
from api.domain.models import CardType, Position, Stage
from api.repositories.memory import create_memory_repositories
from api.repositories.mock_data import build_players
from api.repositories.mongo import create_mongo_repositories
from api.simulation.base import MatchContext
from api.simulation.engine import EngineMatchSimulator, default_sheet, user_sheet
from conftest import USER_SQUAD, Cup, make_client, mock_mongo_db

REAL_FILE = Path(__file__).resolve().parents[3] / "pipeline-dados/artefatos/jogadores_copa_america_2024_filtrado.csv"
PLAYERS = build_players()


def squad(squad_id: str):
    return [p for p in PLAYERS if p.squad_id == squad_id and p.is_current]


def context(seed: int, match_id: str = "G-A-R1-1", stage: Stage = Stage.GROUP) -> MatchContext:
    return MatchContext(
        home=default_sheet("brazil", squad("brazil")),
        away=default_sheet("peru", squad("peru")),
        stage=stage,
        needs_winner=stage is not Stage.GROUP,
        seed=seed,
        match_id=match_id,
    )


def engine_client(repositories=None, seed: int = 11):
    seeds = iter(range(seed, seed + 1000))
    container = build_container(
        repositories=repositories or create_memory_repositories(),
        simulator=EngineMatchSimulator(),
        rng=random.Random(seed),
        session_seed=lambda: next(seeds),
    )
    return make_client(container)


def error_code(response) -> str:
    return response.get_json()["error"]["code"]


# --- The adapter ------------------------------------------------------------------------------


@pytest.mark.parametrize("seed", range(40))
def test_goals_cards_and_injuries_follow_the_engine(seed):
    ctx = context(seed)
    result = EngineMatchSimulator().simulate_match(ctx)

    assert len(result.goals) == result.home_goals + result.away_goals
    sides = {"brazil": ctx.home, "peru": ctx.away}
    for goal in result.goals:
        sheet = sides[goal.squad_id]
        scorer = next(i for i, p in enumerate(sheet.players) if p.id == goal.player_id)
        assert sheet.slots[scorer] != "GK"
        assert 0 <= goal.minute < 90
    assert sum(g.squad_id == "brazil" for g in result.goals) == result.home_goals
    assert [g.minute for g in result.goals] == sorted(g.minute for g in result.goals)
    for card in result.cards:
        sheet = sides[card.squad_id]
        assert card.player_id in {p.id for p, slot in zip(sheet.players, sheet.slots) if slot != "GK"}
        assert card.second_yellow is False or card.type is CardType.RED
    for injury in result.injuries:
        assert injury.player_id in {p.id for p in sides[injury.squad_id].players}
        assert 1 <= injury.matches_out <= 3
    assert result.home_penalties is None and result.away_penalties is None


def test_a_match_is_reproducible_from_the_seed_and_the_match_id():
    first = EngineMatchSimulator().simulate_match(context(5))

    assert EngineMatchSimulator().simulate_quick(context(5)) == first
    others = [EngineMatchSimulator().simulate_match(context(5, f"G-B-R{i}-1")) for i in range(1, 4)]
    others += [EngineMatchSimulator().simulate_match(context(seed)) for seed in range(6, 12)]
    assert any(other != first for other in others)


def test_penalties_only_on_knockout_draws():
    level = [seed for seed in range(200) if _level(seed)]
    assert level, "no level match in 200 seeds"

    for seed in level[:5]:
        knockout = EngineMatchSimulator().simulate_match(context(seed, "QF1", Stage.QUARTER_FINAL))
        group = EngineMatchSimulator().simulate_match(context(seed, "QF1", Stage.GROUP))
        assert knockout.home_penalties != knockout.away_penalties
        assert (group.home_penalties, group.away_penalties) == (None, None)
        assert (knockout.home_goals, knockout.away_goals) == (group.home_goals, group.away_goals)


def _level(seed: int) -> bool:
    result = EngineMatchSimulator().simulate_match(context(seed, "QF1", Stage.QUARTER_FINAL))
    return result.home_goals == result.away_goals


def test_an_injury_lasts_the_same_on_every_replay():
    injured = [(seed, r) for seed in range(300) if (r := EngineMatchSimulator().simulate_match(context(seed))).injuries]
    assert injured, "no injury in 300 seeds"

    seed, result = injured[0]
    assert EngineMatchSimulator().simulate_match(context(seed)).injuries == result.injuries


def test_a_red_for_two_yellows_keeps_both_cards():
    found = []
    for seed in range(3000):
        result = EngineMatchSimulator().simulate_match(context(seed))
        found += [(result, c) for c in result.cards if c.second_yellow]
        if found:
            break
    assert found, "no second yellow in 3000 seeds"

    result, red = found[0]
    yellows = [c for c in result.cards if c.player_id == red.player_id and c.type is CardType.YELLOW]
    assert red.type is CardType.RED and len(yellows) == 1
    assert yellows[0].minute <= red.minute


# --- Slot assignment -----------------------------------------------------------------------------


def test_the_users_xi_is_placed_preferring_exact_positions():
    brazil = squad("brazil")
    xi = [brazil[0], *[p for p in brazil if p.position is Position.DEF][:4],
          *[p for p in brazil if p.position is Position.MID][:4], *[p for p in brazil if p.position is Position.FW][:2]]

    sheet = user_sheet("brazil", xi, "4-4-2")

    assert sheet.slots == list(FORMATIONS["4-4-2"])
    assert sorted(p.id for p in sheet.players) == sorted(p.id for p in xi)
    for player, slot in zip(sheet.players, sheet.slots):
        assert sector_of(slot) is player.position


def test_simulate_returns_who_played_where(client, cup):
    cup.start()
    lineup = cup.lineup()

    match = cup.post("simulate", {"players": lineup}).get_json()["match"]  # no formation: 4-4-2

    assert [entry["slot"] for entry in match["lineup"]] == list(FORMATIONS["4-4-2"])
    assert sorted(entry["player"]["id"] for entry in match["lineup"]) == sorted(lineup)
    assert all(entry["player"]["name"] for entry in match["lineup"])


def test_unknown_formation_and_a_lineup_that_does_not_fit_are_rejected_before_anything_changes(cup):
    cup.start()
    available = cup.get("available-players").get_json()["available"]
    by_position = {pos: [p["id"] for p in available if p["position"] == pos] for pos in ("GK", "DEF", "MID", "FW")}
    five_at_the_back = [by_position["GK"][0], *by_position["DEF"][:5], *by_position["MID"][:4], by_position["FW"][0]]

    unknown = cup.post("simulate", {"players": cup.lineup(), "formation": "2-3-5"})
    misfit = cup.post("simulate", {"players": five_at_the_back, "formation": "4-4-2"})

    assert (unknown.status_code, error_code(unknown)) == (400, "INVALID_FORMATION")
    assert (misfit.status_code, error_code(misfit)) == (400, "LINEUP_DOES_NOT_FIT_FORMATION")
    assert "no slot for" in misfit.get_json()["error"]["message"]
    assert cup.get("history").get_json()["matches"] == []  # no round was played
    assert cup.post("simulate", {"players": five_at_the_back, "formation": "3-5-2"}).status_code == 400
    assert cup.post("simulate", {"players": cup.lineup(), "formation": "4-4-2"}).status_code == 200


def _sideline(repositories, session_id: str, player_ids, matches: int = 9) -> None:
    session = repositories.sessions.get(session_id)
    for player_id in player_ids:
        session.player_status[player_id].injured_matches = matches
    repositories.sessions.save(session)


def test_with_every_goalkeeper_out_a_whole_session_finishes():
    repositories = create_memory_repositories()
    cup = Cup(engine_client(repositories), squad="uruguay")
    cup.start()
    keepers = [p["id"] for p in cup.get("available-players").get_json()["available"] if p["position"] == "GK"]
    _sideline(repositories, cup.id, keepers, matches=99)

    step = "NEXT_ROUND"
    while step not in ("ELIMINATED", "FINISHED"):
        available = cup.get("available-players").get_json()["available"]
        assert not [p for p in available if p["position"] == "GK"]
        xi = []
        for position, count in (("DEF", 4), ("MID", 5), ("FW", 2)):
            xi += [p["id"] for p in available if p["position"] == position][:count]
        response = cup.post("simulate", {"players": xi, "formation": "4-4-2"})
        assert response.status_code == 200, response.get_json()
        match = response.get_json()["match"]
        assert match["lineup"][0]["slot"] == "GK" and match["lineup"][0]["player"]["id"] in xi
        step = response.get_json()["next"]["step"]
        if step == "AWAITING_PLAYOFFS_DRAW":
            cup.get("playoffs-draw")
    if step == "ELIMINATED":
        cup.post("simulate-all")
    assert cup.get("history").get_json()["phase"] == "FINISHED"


def test_the_highest_reflexes_stand_in_that_does_not_fit_gives_way_to_one_that_does():
    repositories = create_memory_repositories()
    cup = Cup(engine_client(repositories), squad="chile")
    cup.start()
    available = cup.get("available-players").get_json()["available"]
    _sideline(repositories, cup.id, [p["id"] for p in available if p["position"] == "GK"])
    ids = {pos: [p["id"] for p in available if p["position"] == pos] for pos in ("DEF", "MID", "FW")}
    # 4 DEF, 4 MID, 3 FW for a 4-4-2: only a forward can leave for goal and still let the rest fit.
    xi = ids["DEF"][:4] + ids["MID"][:4] + ids["FW"][:3]
    defender = ids["DEF"][0]
    players = repositories.players
    players._players[defender] = replace(  # the defender has the best reflexes, but a 3-4-3 does not fit
        players._players[defender], attributes={**players._players[defender].attributes, "goalkeeping_reflexes": 90}
    )

    response = cup.post("simulate", {"players": xi, "formation": "4-4-2"})

    assert response.status_code == 200, response.get_json()
    keeper = response.get_json()["match"]["lineup"][0]["player"]["id"]
    assert keeper in ids["FW"][:3]


# --- Determinism and the full flow ------------------------------------------------------------------


def _play_cup(client, squad_id: str) -> dict:
    cup = Cup(client, squad=squad_id)
    cup.start()
    step = "NEXT_ROUND"
    while step not in ("ELIMINATED", "FINISHED"):
        step = cup.play()["next"]["step"]
        if step == "AWAITING_PLAYOFFS_DRAW":
            cup.get("playoffs-draw")
    if step == "ELIMINATED":
        cup.post("simulate-all")
    history = cup.get("history").get_json()
    history.pop("sessionId")
    return history


@pytest.mark.parametrize("backend", ["memory", "mongo"])
def test_a_whole_cup_on_the_engine_is_reproducible_from_the_session_seed(backend):
    def repositories():
        return create_memory_repositories() if backend == "memory" else create_mongo_repositories(mock_mongo_db(), seed_mock=True)

    first = _play_cup(engine_client(repositories(), seed=2026), USER_SQUAD)
    again = _play_cup(engine_client(repositories(), seed=2026), USER_SQUAD)
    other = _play_cup(engine_client(repositories(), seed=99), USER_SQUAD)

    assert first["phase"] == "FINISHED" and len(first["matches"]) == 32
    assert first == again
    assert first != other
    for match in first["matches"]:
        result = match["result"]
        assert result["homeGoals"] == sum(g["squad"] == match["home"]["id"] for g in result["goals"])
        assert all(0 <= event["minute"] < 90 for event in result["goals"] + result["cards"] + result["injuries"])
        if match["stage"] != "GROUP":
            assert result["winner"] in (match["home"]["id"], match["away"]["id"])
    for group in first["groups"]:
        assert sum(row["yellowCards"] + row["redCards"] for row in group["standings"]) >= 0


def test_the_bracket_follows_the_group_positions():
    cup = Cup(engine_client(seed=5))
    cup.start()
    cup.play_group_stage()
    results = cup.get("round-results").get_json()
    tables = {g["name"]: [row["squad"]["id"] for row in g["standings"]] for g in results["groups"]}

    quarter_finals = cup.get("playoffs-draw").get_json()["quarterFinals"]

    assert [s["id"] for s in results["qualified"]] == [t for name in "ABCD" for t in tables[name][:2]]
    pairs = [(m["home"]["id"], m["away"]["id"]) for m in quarter_finals]
    assert pairs == [
        (tables["A"][0], tables["B"][1]),
        (tables["B"][0], tables["A"][1]),
        (tables["D"][0], tables["C"][1]),
        (tables["C"][0], tables["D"][1]),
    ]


def test_meta_says_what_runs(client):
    assert client.get("/meta").get_json() == {"simulator": "ScriptedSimulator", "catalogVersion": "mock"}
    assert engine_client().get("/meta").get_json()["catalogVersion"] == "mock"
    settings_client = make_client(build_container(rng=random.Random(1)))
    assert settings_client.get("/meta").get_json() == {"simulator": "mock", "catalogVersion": "mock"}


# --- The catalogue and the engine agree on positions ----------------------------------------------------


def test_the_servers_sector_mapping_is_the_engines_for_every_dataset_code():
    with open(REAL_FILE, newline="", encoding="utf-8") as handle:
        codes = {code.strip() for row in csv.DictReader(handle) for code in row["player_positions"].split(",")}

    assert codes >= {"GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LM", "RM", "LW", "RW", "ST", "CF"}
    for code in codes:
        assert sector_of(code) is Position(POSITION_SECTORS[engine_canonical(code)]), code


def test_a_player_without_engine_data_is_refused_not_guessed():
    from api.simulation.engine import IncompleteCatalogError, engine_player

    player = squad("brazil")[0]
    no_attributes = replace(player, attributes={})
    no_positions = replace(player, positions=())
    partial = replace(player, attributes={k: v for k, v in player.attributes.items() if k != "mentality_penalties"})

    with pytest.raises(IncompleteCatalogError, match="mentality_penalties"):
        engine_player(partial)
    with pytest.raises(IncompleteCatalogError, match="positions"):
        engine_player(no_positions)
    with pytest.raises(IncompleteCatalogError) as error:
        default_sheet("brazil", [no_attributes, *squad("brazil")[1:]])
    assert (error.value.status, error.value.code) == (500, "CATALOG_INCOMPLETE")
    assert str(player.id) in error.value.message
