import pytest

from conftest import USER_SQUAD, Cup
from jsonschema import validate
import threading

SESSION_SCHEMA = {
    "type": "object",
    "properties": {
        "session": {
            "type": "object",
            "required": ["id", "createdAt", "phase", "squadId", "callUp", "playerStatus", "round", "userEliminated"],
            "properties": {
                "id": {"type": "string"},
                "createdAt": {"type": "string", "format": "date-time"},
                "phase": {"type": "string"},
                "squadId": {"type": ["string", "null"]},
                "callUp": {"type": "array", "items": {"type": "integer"}},
                "playerStatus": {"type": "object"},
                "round": {"type": "integer"},
                "userEliminated": {"type": "boolean"},
            },
        }
    },
}

def test_create_session(client):
    resp = client.post("/session")
    assert resp.status_code == 201

    payld = resp.get_json()
    assert "sessionId" in payld
    assert isinstance(payld["sessionId"], str)

def test_session_json_contract(client, cup):
    resp = client.get(f"/session/{cup.id}")
    inst = resp.get_json()
    schema = SESSION_SCHEMA
    validate(inst, schema)
    
def test_initial_state(client, cup):
    resp = client.get(f"/session/{cup.id}")
    assert resp.status_code == 200

    session = resp.get_json()["session"]
    assert session == {
        "id": cup.id,
        "createdAt": session["createdAt"],
        "phase": "CREATED",
        "squadId": None,
        "callUp": [],
        "playerStatus": {},
        "round": 0,
        "userEliminated": False,
    }

def test_state_after_call_up(client, cup):
    callResp = cup.call_up()
    assert callResp.status_code == 200

    resp = client.get(f"/session/{cup.id}")
    session = resp.get_json()["session"]
    assert session["phase"] == "CALLED_UP"
    assert session["squadId"] == USER_SQUAD
    assert len(session["callUp"]) == 26
    assert isinstance(session["callUp"][0], int)

def test_state_after_red_card(client, cup, simulator):
    cup.start()
    lineup = cup.lineup()
    playerRd = lineup[1]
    simulator.red_card_for = playerRd
    cup.play()
    resp = client.get(f"/session/{cup.id}")
    session = resp.get_json()["session"]

    assert session["round"] == 1
    assert session["phase"] == "GROUP_STAGE"
    plKey = str(playerRd)
    assert plKey in session["playerStatus"]
    plStatus = session["playerStatus"][plKey]
    assert plStatus == {
        "yellowCards": 0,
        "suspendedMatches": 1,
        "suspensionReason": "SUSPENDED_RED",
        "injuredMatches": 0,
        "available": False,
        "matchesRemaining": 1,
    }

@pytest.mark.xfail(reason="Race condition na simulação")
def test_concurrent_play(cup):
    cup.start()
    payld = {"players": cup.lineup(), "formation": "4-4-2"}
    responses = []
    def worker():
        resp = cup.post("simulate", payld)
        responses.append(resp)
    thread1 = threading.Thread(target=worker)
    thread2 = threading.Thread(target=worker)

    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()

    status = sorted([r.status_code for r in responses])
    assert status == [200, 409]

def test_state_end_sim(client, cup, simulator):
    simulator.user_wins = lambda stage: False
    cup.start()
    cup.play_group_stage()
    cup.post("simulate-all")

    resp = client.get(f"/session/{cup.id}")
    assert resp.status_code == 200
    session = resp.get_json()["session"]
    assert session["phase"] == "FINISHED"
    assert session["userEliminated"] is True

def test_session_not_found(client):
    resp = client.get("/session/invalid-session-id")
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "SESSION_NOT_FOUND"