import conftest
from jsonschema import validate

LOGIN_SCHEMA = {
    "type": "object",
    "properties": {
        "user": {
            "type": "object",
            "required": ["id", "sessionId", "email"],
            "properties": {
                "id": {"type": "string"},
                "sessionId": {"type": "string"},
                "email": {"type": "string"},
            },
        }
    },
}

def test_login_json_contract(client):
    payload = {
        "email": "example@domain.com",
        "password": "johnandjanedoe2001"
    }
    reg_resp = client.post("/register", json=payload)
    assert reg_resp.status_code == 201

    login_resp = client.post("/login", json=payload)
    assert login_resp.status_code == 200

    inst = login_resp.get_json()
    schema = LOGIN_SCHEMA
    validate(inst, schema)
    assert inst["user"]["email"] == payload["email"]
