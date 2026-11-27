"""Functional tests against a running stack (docker compose up), over real HTTP.

Skipped unless API_BASE_URL is set. With MONGO_URI (and optionally MONGO_DB) set,
they also check what was written to the database, and, when the stack was seeded
with the real catalogue (catalog_meta present), the real players.

    API_BASE_URL=http://127.0.0.1:5000 MONGO_URI=mongodb://127.0.0.1:27018 uv run pytest tests/functional

Behind AWS API Gateway, set API_KEY too: it is sent as the x-api-key header, and a
request without it must be refused (the database is private there, so no MONGO_URI):

    API_BASE_URL=https://<id>.execute-api.us-east-2.amazonaws.com/v1 API_KEY=<key> uv run pytest tests/functional
"""

import json as jsonlib
import os
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from functools import cache

import pytest
from pymongo import MongoClient

from conftest import Cup
from openapi_check import response_problems

BASE_URL = os.environ.get("API_BASE_URL", "").rstrip("/")
MONGO_URI = os.environ.get("MONGO_URI")
API_KEY = os.environ.get("API_KEY")
MONGO_DB = os.environ.get("MONGO_DB", "copa")
QUOTAS = {"GK": 3, "DEF": 8, "MID": 8, "FW": 7}

pytestmark = pytest.mark.skipif(not BASE_URL, reason="API_BASE_URL is not set; start the stack first")


class LiveResponse:
    def __init__(self, status_code: int, body: bytes):
        self.status_code = status_code
        self.body = body

    def get_json(self, silent: bool = False):
        """Like Flask's: with `silent`, a body that is not JSON gives None instead of an error."""
        try:
            return jsonlib.loads(self.body) if self.body else None
        except ValueError:
            if silent:
                return None
            raise


class LiveClient:
    """Speaks HTTP to the running API with the same interface as Flask's test client.

    Every response is checked against the OpenAPI document the server publishes.
    """

    def get(self, path: str) -> LiveResponse:
        return self.send("GET", path)

    def post(self, path: str, json=None) -> LiveResponse:
        data = None if json is None else jsonlib.dumps(json).encode()
        return self.send("POST", path, data, "application/json")

    def send(self, method: str, path: str, data: bytes | None = None, content_type: str | None = None):
        response = _request(method, path, data, content_type)
        route = urllib.parse.urlsplit(path).path
        body = response.get_json(silent=True)
        problems = response_problems(live_spec(), method, route, response.status_code, body)
        assert not problems, "\n".join(problems)
        return response


@cache
def live_spec() -> dict:
    return _request("GET", "/openapi.json").get_json()


def _request(
    method: str, path: str, data: bytes | None = None, content_type: str | None = None, api_key: str | None = API_KEY
) -> LiveResponse:
    headers = {"Content-Type": content_type} if content_type else {}
    if api_key:
        headers["x-api-key"] = api_key
    request = urllib.request.Request(BASE_URL + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return LiveResponse(response.status, response.read())
    except urllib.error.HTTPError as error:
        return LiveResponse(error.code, error.read())


@pytest.fixture
def client() -> LiveClient:
    return LiveClient()


@pytest.fixture
def cup(client) -> Cup:
    return Cup(client, squad="peru")


@pytest.fixture
def db():
    if not MONGO_URI:
        pytest.skip("MONGO_URI is not set")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    yield client[MONGO_DB]
    client.close()


@pytest.fixture
def catalog_meta(db) -> dict:
    meta = db.catalog_meta.find_one({"_id": "catalog"})
    if meta is None:
        pytest.skip("the stack serves the mock catalogue (no catalog_meta)")
    return meta


def error_code(response: LiveResponse) -> str:
    return response.get_json()["error"]["code"]


def play_to_the_end(cup: Cup) -> dict:
    """Plays every match the user has, finishes the cup and returns the history."""
    step = "NEXT_ROUND"
    while step not in ("ELIMINATED", "FINISHED"):
        step = cup.play()["next"]["step"]
        assert cup.get("round-results").status_code == 200
        if step == "AWAITING_PLAYOFFS_DRAW":
            assert cup.get("playoffs-draw").status_code == 200
    if step == "ELIMINATED":
        assert cup.post("simulate-all").status_code == 200
    return cup.get("history").get_json()


# --- Catalogue ------------------------------------------------------------------


def test_catalogue_endpoints(client):
    squads = client.get("/squads").get_json()["squads"]
    keepers = client.get("/peru/players?position=GK").get_json()["players"]
    presets = client.get("/peru/presets").get_json()["presets"]

    assert len(squads) == 16
    assert keepers and {player["position"] for player in keepers} == {"GK"}
    assert [preset["id"] for preset in presets] == ["current", "legends", "random"]
    for preset in presets:
        assert Counter(player["position"] for player in preset["players"]) == QUOTAS
    assert client.get("/peru/players?position=striker").status_code == 400
    assert client.get("/atlantis/players").status_code == 404


def test_catalogue_is_served_from_the_database(client, db):
    squads = client.get("/squads").get_json()["squads"]
    stored = {doc["_id"]: doc for doc in db.squads.find()}

    assert {squad["id"] for squad in squads} == set(stored)
    for squad in squads:  # byte-for-byte, accents included (Bolívia, Panamá, ...)
        assert squad["name"] == stored[squad["id"]]["name"]
    assert db.players.count_documents({"squad_id": "peru"}) == len(client.get("/peru/players").get_json()["players"])


def test_the_real_catalogue_is_served(client, db, catalog_meta):
    squads = {squad["id"]: squad for squad in client.get("/squads").get_json()["squads"]}
    argentina = client.get("/argentina/players").get_json()["players"]

    assert len(squads) == 16
    assert squads["canada"]["name"] == "Canadá"
    assert "haiti" not in squads
    messi = [player for player in argentina if player["name"] == "L. Messi"]
    assert len(messi) == 1 and messi[0]["position"] == "FW"
    assert db.players.count_documents({}) == catalog_meta["players"]
    assert db.players.count_documents({"is_current": True}) == 16 * 26 - 2  # Jamaica and Panama list 25


def test_the_stack_runs_the_engine(client):
    meta = client.get("/meta").get_json()

    assert meta["simulator"] == "engine"
    assert meta["catalogVersion"]


def test_engine_results_look_like_the_engines(cup, capsys):
    cup.start()
    history = play_to_the_end(cup)

    goals = 0
    for match in history["matches"]:
        result = match["result"]
        goals += result["homeGoals"] + result["awayGoals"]
        # minutes fall inside the engine's six 15-minute cycles
        assert all(0 <= event["minute"] < 90 for event in result["goals"] + result["cards"] + result["injuries"])
        assert len(result["goals"]) == result["homeGoals"] + result["awayGoals"]
    user_matches = [m for m in history["matches"] if m["lineup"] is not None]
    assert user_matches and all(len(m["lineup"]) == 11 for m in user_matches)
    with capsys.disabled():
        print(f"\naverage goals per match over {len(history['matches'])} matches: {goals / len(history['matches']):.2f}")


# --- A whole cup ----------------------------------------------------------------


def test_a_full_cup_from_session_to_history(cup):
    draw = cup.start()
    assert {squad["id"] for group in draw["groups"] for squad in group["squads"]} >= {"peru"}

    history = play_to_the_end(cup)

    assert history["phase"] == "FINISHED"
    assert history["userSquad"]["id"] == "peru"
    assert history["placement"] is not None
    assert len(history["matches"]) == 32
    assert len({squad["id"] for squad in history["podium"].values()}) == 4
    assert history["userPath"][0]["stage"] == "GROUP"
    for match in history["matches"]:
        result = match["result"]
        assert result["homeGoals"] == sum(goal["squad"] == match["home"]["id"] for goal in result["goals"])


def test_a_finished_cup_is_persisted(cup, db):
    cup.start()
    history = play_to_the_end(cup)

    session = db.sessions.find_one({"_id": cup.id})
    assert session["phase"] == "FINISHED"
    assert session["squad_id"] == "peru"
    assert len(session["call_up"]) == 26
    assert db.tournaments.find_one({"_id": cup.id})["groups"].keys() == {"A", "B", "C", "D"}
    assert db.matches.count_documents({"session_id": cup.id}) == 32
    assert db.matches.count_documents({"session_id": cup.id, "played": False}) == 0
    final = db.matches.find_one({"session_id": cup.id, "stage": "FINAL"})
    assert history["bracket"]["final"]["result"]["homeGoals"] == final["result"]["home_goals"]


def test_group_results_stay_hidden_until_their_round(cup, db):
    cup.start()
    hidden = db.matches.count_documents({"session_id": cup.id, "played": False, "result": {"$ne": None}})
    cup.play()

    assert hidden == 21  # the 24 group matches minus the user's 3, pre-simulated at the draw
    revealed = cup.get("history").get_json()["matches"]
    assert len(revealed) == 8
    assert {match["round"] for match in revealed} == {1}


def test_sessions_are_isolated(client):
    first, second = Cup(client, squad="peru"), Cup(client, squad="chile")
    first.start()
    second.start()
    first.play()

    assert first.get("round-results").get_json()["round"] == 1
    assert error_code(second.get("round-results")) == "NO_ROUND_PLAYED"
    assert second.get("history").get_json()["userSquad"]["id"] == "chile"


# --- Errors ---------------------------------------------------------------------


def test_errors_are_json(client, cup):
    unknown = client.get("/no-such-session/history")
    not_json = client.send("POST", f"/{cup.id}/call-up", b"not json", "application/json")
    too_early = cup.get("draw")
    no_route = client.get("/a/b/c")

    assert (unknown.status_code, error_code(unknown)) == (404, "SESSION_NOT_FOUND")
    assert (not_json.status_code, error_code(not_json)) == (400, "INVALID_BODY")
    assert (too_early.status_code, error_code(too_early)) == (409, "CALL_UP_REQUIRED")
    assert (no_route.status_code, error_code(no_route)) == (404, "NOT_FOUND")


def test_out_of_order_steps_are_rejected(cup):
    cup.start()
    cup.play()

    assert error_code(cup.post("simulate-all")) == "USER_STILL_PLAYING"
    assert error_code(cup.get("playoffs-draw")) == "GROUP_STAGE_NOT_FINISHED"
    assert error_code(cup.call_up()) == "DRAW_ALREADY_DONE"
    bad_lineup = cup.post("simulate", {"players": cup.lineup()[:10]})
    assert (bad_lineup.status_code, error_code(bad_lineup)) == (400, "INVALID_LINEUP")


# --- Documentation ----------------------------------------------------------------


def test_docs_are_served(client):
    page = client.send("GET", "/docs")
    spec = live_spec()

    assert page.status_code == 200
    assert b"swagger-ui-bundle.js" in page.body
    assert spec["openapi"] == "3.1.0"
    assert "/{sessionId}/simulate" in spec["paths"]


# --- API Gateway --------------------------------------------------------------------


@pytest.mark.skipif(not API_KEY, reason="API_KEY is not set (not behind API Gateway)")
def test_requests_without_the_api_key_are_refused():
    without = _request("GET", "/squads", api_key=None)
    wrong = _request("GET", "/squads", api_key="not-the-key")

    assert without.status_code == 403
    assert wrong.status_code == 403
    assert _request("GET", "/squads").status_code == 200
