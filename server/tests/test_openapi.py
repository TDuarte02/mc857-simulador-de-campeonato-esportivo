"""The OpenAPI document and the Swagger UI page.

Response shapes are not tested here: every request in the suite goes through
SpecCheckedClient (conftest.py), which checks each response against the document.
"""

import re

import pytest

from api.container import build_container
from api.controllers.docs_controller import SWAGGER_UI_VERSION
from api.controllers.openapi import EXAMPLE_CALL_UP, EXAMPLE_LINEUP, openapi_spec
from api.repositories.memory import create_memory_repositories
from conftest import make_client
from openapi_check import find_operation, response_problems, schema_problems

SPEC = openapi_spec()
METHODS = {"get", "post", "put", "patch", "delete"}


@pytest.fixture
def client():
    return make_client(build_container(repositories=create_memory_repositories()))


def documented_operations():
    for path, operations in SPEC["paths"].items():
        for method, operation in operations.items():
            if method in METHODS:
                yield path, method, operation


def flask_rule_to_template(rule: str) -> str:
    """/<session_id>/draw -> /{sessionId}/draw"""

    def camel(match: re.Match) -> str:
        first, *rest = match.group(1).split("_")
        return "{" + first + "".join(word.title() for word in rest) + "}"

    return re.sub(r"<(?:[^:>]+:)?([^>]+)>", camel, rule)


# --- Serving ----------------------------------------------------------------------


def test_openapi_json_serves_the_document(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.get_json() == SPEC
    assert SPEC["openapi"] == "3.1.0"


def test_docs_page_loads_the_pinned_swagger_ui(client):
    response = client.get("/docs")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert f"swagger-ui-dist@{SWAGGER_UI_VERSION}/swagger-ui-bundle.js" in page
    assert page.count('integrity="sha384-') == 2
    assert 'url: "/openapi.json"' in page


def test_root_redirects_to_the_docs(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"] == "/docs"


# --- The document matches the code ----------------------------------------------


def test_every_route_is_documented_and_every_documented_route_exists(client):
    app = client.application
    routes = {
        (flask_rule_to_template(rule.rule), method.lower())
        for rule in app.url_map.iter_rules()
        if not rule.endpoint.startswith("docs.")
        for method in rule.methods - {"HEAD", "OPTIONS"}
    }
    documented = {(path, method) for path, method, _ in documented_operations()}

    assert routes == documented


def test_every_reference_resolves():
    refs = set()

    def collect(node):
        if isinstance(node, dict):
            refs.update([node["$ref"]] if "$ref" in node else [])
            for value in node.values():
                collect(value)
        elif isinstance(node, list):
            for value in node:
                collect(value)

    collect(SPEC)
    schemas = SPEC["components"]["schemas"]

    assert refs, "the document has no references at all"
    for ref in refs:
        assert ref.removeprefix("#/components/schemas/") in schemas, ref


def test_operations_are_complete():
    tags = {tag["name"] for tag in SPEC["tags"]}
    ids = [operation["operationId"] for _, _, operation in documented_operations()]

    assert len(ids) == len(set(ids))
    for path, method, operation in documented_operations():
        assert set(operation["tags"]) <= tags, (path, method)
        assert operation["summary"] and operation["description"], (path, method)
        assert any(status.startswith("2") for status in operation["responses"]), (path, method)
        placeholders = set(re.findall(r"\{([^}]+)\}", path))
        path_params = {p["name"] for p in operation.get("parameters", []) if p["in"] == "path"}
        assert placeholders == path_params, (path, method)


def test_documented_examples_are_accepted_by_the_api(client):
    session_id = client.post("/session").get_json()["sessionId"]

    call_up = client.post(f"/{session_id}/call-up", json={"squad": "brazil", "players": EXAMPLE_CALL_UP})
    client.get(f"/{session_id}/draw")
    simulate = client.post(f"/{session_id}/simulate", json={"players": EXAMPLE_LINEUP, "formation": "4-4-2"})

    assert call_up.status_code == 200
    assert simulate.status_code == 200


# --- The checker itself -----------------------------------------------------------


def test_checker_matches_paths_to_their_templates():
    assert find_operation(SPEC, "GET", "/squads")["operationId"] == "listSquads"
    assert find_operation(SPEC, "GET", "/brazil/players")["operationId"] == "listPlayers"
    assert find_operation(SPEC, "POST", "/0b4e/simulate")["operationId"] == "simulateMatch"
    assert find_operation(SPEC, "DELETE", "/squads") is None
    assert find_operation(SPEC, "GET", "/docs") is None


def test_checker_reports_responses_that_break_the_document():
    squad = {"id": "brazil", "name": "Brasil", "flag": "https://x", "federation": "CONMEBOL"}

    def problems(body, status=200, path="/squads"):
        return response_problems(SPEC, "GET", path, status, body)

    assert problems({"squads": [squad]}) == []
    assert "missing 'flag'" in problems({"squads": [{k: v for k, v in squad.items() if k != "flag"}]})[0]
    assert "undocumented field 'extra'" in problems({"squads": [{**squad, "extra": 1}]})[0]
    assert "is not one of" in problems({"squads": [{**squad, "federation": "UEFA"}]})[0]
    assert "expected array" in problems({"squads": None})[0]
    assert "status 500 is not documented" in problems({}, status=500)[0]
    unknown_code = {"error": {"code": "SOMETHING_ELSE", "message": "x"}}
    assert "is not one of" in problems(unknown_code, status=404, path="/brazil/players")[0]


def test_checker_refuses_schemas_it_cannot_check():
    with pytest.raises(AssertionError, match="does not support"):
        schema_problems(SPEC, 1, {"oneOf": [{"type": "integer"}]})
