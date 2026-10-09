import random
from collections import Counter

import pytest

from api import create_app
from api.container import build_container
from api.domain.models import Stage
from conftest import USER_SQUAD, Cup

QUOTAS = {"GK": 3, "DEF": 8, "MID": 8, "FW": 7}


def error_code(response) -> str:
    return response.get_json()["error"]["code"]


# --- Catalogue ------------------------------------------------------------------


def test_squads_have_name_flag_and_federation(client):
    squads = client.get("/squads").get_json()["squads"]

    assert len(squads) == 16
    brazil = next(squad for squad in squads if squad["id"] == "brazil")
    assert brazil == {
        "id": "brazil",
        "name": "Brasil",
        "flag": "https://flagcdn.com/w320/br.png",
        "federation": "CONMEBOL",
    }
    assert {squad["federation"] for squad in squads} == {"CONMEBOL", "CONCACAF"}


def test_players_can_be_filtered_by_position(client):
    players = client.get("/brazil/players").get_json()["players"]
    goalkeepers = client.get("/brazil/players?position=gk").get_json()["players"]

    assert set(players[0]) == {"id", "name", "age", "position", "overall"}
    assert len(players) > 26
    assert goalkeepers and all(player["position"] == "GK" for player in goalkeepers)
    assert len(goalkeepers) < len(players)


def test_unknown_position_and_squad_are_rejected(client):
    assert client.get("/brazil/players?position=striker").status_code == 400
    assert client.get("/atlantis/players").status_code == 404
    assert client.get("/atlantis/presets").status_code == 404


def test_presets_are_valid_call_ups(client):
    presets = client.get("/brazil/presets").get_json()["presets"]

    assert [preset["id"] for preset in presets] == ["current", "legends", "random"]
    for preset in presets:
        assert Counter(player["position"] for player in preset["players"]) == QUOTAS


# --- Call-up and draw -----------------------------------------------------------


def test_call_up_validates_size_quotas_and_ownership(cup, client):
    players = cup.preset()
    spare_keeper = next(
        p["id"] for p in client.get("/brazil/players?position=GK").get_json()["players"] if p["id"] not in players
    )
    foreigner = client.get("/argentina/players").get_json()["players"][0]["id"]

    too_few = cup.post("call-up", {"squad": "brazil", "players": players[:-1]})
    wrong_quota = cup.post("call-up", {"squad": "brazil", "players": [*players[:-1], spare_keeper]})
    not_ours = cup.post("call-up", {"squad": "brazil", "players": [*players[:-1], foreigner]})
    no_body = cup.post("call-up")

    for response in (too_few, wrong_quota, not_ours):
        assert (response.status_code, error_code(response)) == (400, "INVALID_CALL_UP")
    assert (no_body.status_code, error_code(no_body)) == (400, "INVALID_BODY")
    assert cup.call_up().status_code == 200


def test_draw_needs_a_call_up(cup):
    response = cup.get("draw")

    assert (response.status_code, error_code(response)) == (409, "CALL_UP_REQUIRED")


def test_draw_builds_four_groups_with_full_squads(cup):
    draw = cup.start()

    squads = [squad for group in draw["groups"] for squad in group["squads"]]
    assert [group["name"] for group in draw["groups"]] == ["A", "B", "C", "D"]
    assert all(len(group["squads"]) == 4 for group in draw["groups"])
    assert len({squad["id"] for squad in squads}) == 16
    assert USER_SQUAD in {squad["id"] for squad in squads}
    assert all(Counter(p["position"] for p in squad["players"]) == QUOTAS for squad in squads)
    assert len(draw["matches"]) == 24
    assert all(match["result"] is None for match in draw["matches"])


def test_draw_is_stable_and_locks_the_call_up(cup):
    first = cup.start()

    assert cup.get("draw").get_json() == first
    locked = cup.call_up()
    assert (locked.status_code, error_code(locked)) == (409, "DRAW_ALREADY_DONE")


# --- The match loop ---------------------------------------------------------------


def test_round_results_show_the_whole_round_and_the_standings(cup):
    cup.start()
    outcome = cup.play()
    results = cup.get("round-results").get_json()

    assert outcome["match"]["result"]["winner"] == USER_SQUAD
    assert outcome["next"]["step"] == "NEXT_ROUND"
    assert (outcome["next"]["stage"], outcome["next"]["round"]) == ("GROUP", 2)
    assert (results["stage"], results["round"]) == ("GROUP", 1)
    assert len(results["matches"]) == 8
    assert all(match["played"] and match["result"] for match in results["matches"])
    assert results["qualified"] is None
    assert all(row["played"] == 1 for group in results["groups"] for row in group["standings"])


def test_user_wins_the_cup(cup):
    cup.start()

    outcome = cup.play_group_stage()
    results = cup.get("round-results").get_json()
    assert outcome["next"]["step"] == "AWAITING_PLAYOFFS_DRAW"
    assert len(results["qualified"]) == 8
    assert USER_SQUAD in {squad["id"] for squad in results["qualified"]}

    blocked = cup.post("simulate", {"players": cup.lineup()})
    assert (blocked.status_code, error_code(blocked)) == (409, "PLAYOFFS_DRAW_REQUIRED")

    playoffs = cup.get("playoffs-draw").get_json()
    drawn = {match[side]["id"] for match in playoffs["quarterFinals"] for side in ("home", "away")}
    assert drawn == {squad["id"] for squad in results["qualified"]}
    assert cup.get("playoffs-draw").get_json() == playoffs

    quarter = cup.play()
    assert quarter["match"]["stage"] == "QUARTER_FINAL"
    assert (quarter["next"]["step"], quarter["next"]["stage"]) == ("NEXT_ROUND", "SEMI_FINAL")
    assert len(cup.get("round-results").get_json()["advanced"]) == 4

    semi = cup.play()
    assert (semi["next"]["step"], semi["next"]["stage"]) == ("NEXT_ROUND", "FINAL")

    final = cup.play()
    assert final["match"]["stage"] == "FINAL"
    assert final["next"]["step"] == "FINISHED"

    history = cup.get("history").get_json()
    assert history["phase"] == "FINISHED"
    assert history["placement"] == "CHAMPION"
    assert history["podium"]["champion"]["id"] == USER_SQUAD
    assert len(history["matches"]) == 32
    assert [match["stage"] for match in history["userPath"]] == [
        "GROUP", "GROUP", "GROUP", "QUARTER_FINAL", "SEMI_FINAL", "FINAL",
    ]
    assert cup.get("round-results").get_json()["podium"] == history["podium"]

    over = cup.post("simulate", {"players": cup.lineup()})
    assert (over.status_code, error_code(over)) == (409, "TOURNAMENT_FINISHED")


def test_elimination_in_the_groups_then_simulate_all(cup, simulator):
    simulator.user_wins = lambda stage: False
    cup.start()

    early = cup.post("simulate-all")
    assert (early.status_code, error_code(early)) == (409, "USER_STILL_PLAYING")

    outcome = cup.play_group_stage()
    assert outcome["next"] == {"step": "ELIMINATED", "stage": None, "round": None, "opponent": None}
    qualified = cup.get("round-results").get_json()["qualified"]
    assert USER_SQUAD not in {squad["id"] for squad in qualified}

    blocked = cup.post("simulate", {"players": cup.lineup()})
    assert (blocked.status_code, error_code(blocked)) == (409, "USER_ELIMINATED")

    finished = cup.post("simulate-all")
    history = finished.get_json()
    assert finished.status_code == 200
    assert history["phase"] == "FINISHED"
    assert history["placement"] == "GROUP_STAGE"
    assert len(history["matches"]) == 32
    assert len(history["userPath"]) == 3
    assert len({squad["id"] for squad in history["podium"].values()}) == 4
    assert cup.post("simulate-all").get_json() == history
    assert cup.get("history").get_json() == history


def test_quarter_final_loss_eliminates_the_user(cup, simulator):
    simulator.user_wins = lambda stage: stage is Stage.GROUP
    cup.start()
    cup.play_group_stage()
    cup.get("playoffs-draw")

    assert cup.play()["next"]["step"] == "ELIMINATED"
    history = cup.post("simulate-all").get_json()
    assert history["placement"] == "QUARTER_FINALS"
    assert history["bracket"]["final"]["played"]


def test_semi_final_loss_leads_to_the_third_place_match(cup, simulator):
    simulator.user_wins = lambda stage: stage is not Stage.SEMI_FINAL
    cup.start()
    cup.play_group_stage()
    cup.get("playoffs-draw")
    cup.play()

    semi = cup.play()
    assert semi["match"]["result"]["winner"] != USER_SQUAD
    assert (semi["next"]["step"], semi["next"]["stage"]) == ("THIRD_PLACE_MATCH", "THIRD_PLACE")
    assert semi["next"]["opponent"]["id"] != USER_SQUAD

    third = cup.play()
    assert third["match"]["stage"] == "THIRD_PLACE"
    assert third["next"]["step"] == "FINISHED"

    history = cup.get("history").get_json()
    assert history["placement"] == "THIRD_PLACE"
    assert history["podium"]["third"]["id"] == USER_SQUAD
    assert history["bracket"]["final"]["played"]


def test_red_card_makes_the_player_unavailable_for_one_match(cup, simulator):
    cup.start()
    lineup = cup.lineup()
    sent_off = lineup[1]
    simulator.red_card_for = sent_off

    outcome = cup.play()
    availability = cup.get("available-players").get_json()

    assert outcome["match"]["result"]["cards"][0]["type"] == "RED"
    assert [(p["id"], p["reason"], p["matchesRemaining"]) for p in availability["unavailable"]] == [
        (sent_off, "SUSPENDED_RED", 1)
    ]
    assert len(availability["available"]) == 25

    rejected = cup.post("simulate", {"players": lineup})
    assert (rejected.status_code, error_code(rejected)) == (400, "PLAYER_UNAVAILABLE")

    cup.play()
    assert cup.get("available-players").get_json()["unavailable"] == []


def test_lineup_is_validated(cup, client):
    cup.start()
    lineup = cup.lineup()
    available = cup.get("available-players").get_json()["available"]
    second_keeper = [p["id"] for p in available if p["position"] == "GK"][1]
    outsider = client.get("/argentina/players").get_json()["players"][0]["id"]

    for players in (lineup[:10], [*lineup[:10], lineup[0]], [*lineup[:10], second_keeper], [*lineup[:10], outsider]):
        response = cup.post("simulate", {"players": players})
        assert (response.status_code, error_code(response)) == (400, "INVALID_LINEUP")
    wrong_type = cup.post("simulate", {"players": "all of them"})
    assert (wrong_type.status_code, error_code(wrong_type)) == (400, "INVALID_BODY")


# --- State errors -------------------------------------------------------------------


def test_unknown_session_is_not_found(client):
    for method, path in (
        ("get", "draw"),
        ("get", "available-players"),
        ("get", "round-results"),
        ("get", "playoffs-draw"),
        ("get", "history"),
        ("post", "simulate-all"),
    ):
        response = getattr(client, method)(f"/nope/{path}")
        assert (response.status_code, error_code(response)) == (404, "SESSION_NOT_FOUND")


def test_steps_out_of_order_are_conflicts(cup):
    assert error_code(cup.get("available-players")) == "CALL_UP_REQUIRED"
    cup.call_up()

    simulate = cup.post("simulate", {"players": cup.lineup()})
    assert (simulate.status_code, error_code(simulate)) == (409, "DRAW_REQUIRED")
    assert error_code(cup.post("simulate-all")) == "DRAW_REQUIRED"

    cup.get("draw")
    assert error_code(cup.get("round-results")) == "NO_ROUND_PLAYED"
    assert error_code(cup.get("playoffs-draw")) == "GROUP_STAGE_NOT_FINISHED"
    assert cup.get("history").get_json()["matches"] == []


# --- The random mock model ------------------------------------------------------


@pytest.mark.parametrize("seed", range(12))
def test_random_model_always_finishes_a_cup(seed):
    client = create_app(build_container(rng=random.Random(seed))).test_client()
    cup = Cup(client, squad="uruguay")
    cup.start()

    step = "NEXT_ROUND"
    while step not in ("ELIMINATED", "FINISHED"):
        step = cup.play()["next"]["step"]
        assert cup.get("round-results").status_code == 200
        if step == "AWAITING_PLAYOFFS_DRAW":
            assert cup.get("playoffs-draw").status_code == 200
    if step == "ELIMINATED":
        assert cup.post("simulate-all").status_code == 200

    history = cup.get("history").get_json()
    assert history["phase"] == "FINISHED"
    assert history["placement"] is not None
    assert len(history["matches"]) == 32
    assert len({squad["id"] for squad in history["podium"].values()}) == 4
    for match in history["bracket"]["quarterFinals"] + history["bracket"]["semiFinals"]:
        assert match["result"]["winner"] in (match["home"]["id"], match["away"]["id"])
