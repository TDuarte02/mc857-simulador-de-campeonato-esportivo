import pytest

from api import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://copa.example")
    return create_app().test_client()


@pytest.mark.parametrize(
    "origin", ["http://localhost:8080", "http://127.0.0.1:3000", "https://copa.example"]
)
def test_allowed_origins_get_the_headers(client, origin):
    response = client.get("/squads", headers={"Origin": origin})
    assert response.headers["Access-Control-Allow-Origin"] == origin


def test_preflight_allows_json_posts(client):
    response = client.options("/session", headers={"Origin": "http://localhost:8080"})
    assert response.status_code == 200
    assert "POST" in response.headers["Access-Control-Allow-Methods"]
    assert response.headers["Access-Control-Allow-Headers"] == "Content-Type"


@pytest.mark.parametrize(
    "origin", ["https://evil.example", "http://localhost.evil.example", "null"]
)
def test_other_origins_are_refused(client, origin):
    response = client.get("/squads", headers={"Origin": origin})
    assert "Access-Control-Allow-Origin" not in response.headers
