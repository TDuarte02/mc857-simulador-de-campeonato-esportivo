import pytest
from jsonschema import validate

from api.errors import ConflictError
from api.repositories.base import DuplicateEmailError
from api.repositories.memory import InMemoryLoginRepository
from api.repositories.mongo import MongoLoginRepository
from conftest import mock_mongo_db

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


# --- Error paths (each response is also checked against the OpenAPI document) ----

CREDENTIALS = {"email": "ana@example.com", "password": "s3cret-pass"}


def error_code(response) -> str:
    return response.get_json()["error"]["code"]


@pytest.fixture
def registered(client) -> dict:
    response = client.post("/register", json=CREDENTIALS)
    assert response.status_code == 201
    return response.get_json()["user"]


@pytest.mark.parametrize("path", ["/register", "/login"])
@pytest.mark.parametrize(
    "body",
    [
        {"email": "ana@example.com"},
        {"password": "x"},
        {"email": "ana@example.com", "password": 123},
        {"email": 5, "password": "x"},
        {"email": "", "password": ""},
        {"email": "   ", "password": "x"},
        {"email": "ana@example.com", "password": ""},
    ],
)
def test_missing_or_non_string_credentials_are_rejected(client, path, body):
    response = client.post(path, json=body)
    assert (response.status_code, error_code(response)) == (400, "INSUFFICIENT_INFO")


@pytest.mark.parametrize("path", ["/register", "/login"])
def test_body_must_be_a_json_object(client, path):
    response = client.post(path, json=["ana@example.com", "x"])
    assert (response.status_code, error_code(response)) == (400, "INVALID_BODY")


@pytest.mark.parametrize("email", ["ana", "@example.com", "ana@", " @ "])
def test_register_needs_an_email_address(client, email):
    response = client.post("/register", json={"email": email, "password": "x"})
    assert (response.status_code, error_code(response)) == (400, "INVALID_EMAIL")


def test_register_creates_a_session_and_normalizes_the_email(client):
    response = client.post("/register", json={"email": "  Ana@Example.COM ", "password": "x"})
    user = response.get_json()["user"]

    assert user["email"] == "ana@example.com"
    assert client.get(f"/session/{user['sessionId']}").status_code == 200


def test_register_links_an_existing_session(client, cup):
    response = client.post("/register", json={**CREDENTIALS, "sessionId": cup.id})
    assert response.get_json()["user"]["sessionId"] == cup.id


def test_register_with_an_unknown_session_is_not_found(client):
    response = client.post("/register", json={**CREDENTIALS, "sessionId": "nope"})
    assert (response.status_code, error_code(response)) == (404, "SESSION_NOT_FOUND")
    assert client.post("/login", json=CREDENTIALS).status_code == 401  # no account was created


def test_register_with_a_non_string_session_id_is_rejected(client):
    response = client.post("/register", json={**CREDENTIALS, "sessionId": 7})
    assert (response.status_code, error_code(response)) == (400, "INVALID_BODY")


def test_an_email_can_only_register_once(client, registered):
    again = client.post("/register", json={"email": " ANA@example.com", "password": "other"})
    assert (again.status_code, error_code(again)) == (409, "USER_ALREADY_EXISTS")
    # the original password still works
    assert client.post("/login", json=CREDENTIALS).status_code == 200


def test_login_returns_the_account(client, registered):
    response = client.post("/login", json={"email": "ANA@EXAMPLE.COM", "password": CREDENTIALS["password"]})
    assert response.status_code == 200
    assert response.get_json()["user"] == registered


@pytest.mark.parametrize(
    "body",
    [
        {"email": "ana@example.com", "password": "wrong"},
        {"email": "nobody@example.com", "password": "s3cret-pass"},
    ],
)
def test_wrong_password_and_unknown_email_look_the_same(client, registered, body):
    response = client.post("/login", json=body)
    assert (response.status_code, error_code(response)) == (401, "INVALID_CREDENTIALS")


# --- Storage: two registrations racing past the "exists?" check --------------------


@pytest.fixture(params=["memory", "mongo"])
def login_repository(request):
    return InMemoryLoginRepository() if request.param == "memory" else MongoLoginRepository(mock_mongo_db())


def test_the_repository_refuses_a_second_account_for_an_email(login_repository):
    first = login_repository.reg_user("ana@example.com", "hash-1", "s1")

    with pytest.raises(DuplicateEmailError):
        login_repository.reg_user(" ANA@example.com", "hash-2", "s2")
    assert login_repository.find_by_email("ana@example.com") == first


def test_a_lost_race_becomes_a_conflict(client):
    login = client.application.extensions["container"].login
    login.reg_user("ana@example.com", "one", "s1")

    with pytest.raises(ConflictError) as error:
        login.reg_user("ana@example.com", "two", "s2")  # what the loser of a race runs
    assert error.value.code == "USER_ALREADY_EXISTS"
    assert login.auth("ana@example.com", "one").sessionId == "s1"
