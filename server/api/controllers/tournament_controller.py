from flask import Blueprint, jsonify

from api.controllers.http import (
    json_body,
    optional_str,
    require_id_list,
    require_str,
    serializer,
    services,
)

bp = Blueprint("tournament", __name__)


@bp.post("/<session_id>/call-up")
def call_up(session_id: str):
    body = json_body()
    result = services().call_ups.call_up(
        session_id, require_str(body, "squad"), require_id_list(body, "players")
    )
    return jsonify(serializer().call_up(result))


@bp.get("/<session_id>/draw")
def draw(session_id: str):
    return jsonify(serializer().draw(services().draws.draw(session_id)))


@bp.get("/<session_id>/available-players")
def available_players(session_id: str):
    return jsonify(serializer().availability(services().matches.available_players(session_id)))


@bp.post("/<session_id>/simulate")
def simulate(session_id: str):
    body = json_body()
    outcome = services().matches.simulate(
        session_id, require_id_list(body, "players"), optional_str(body, "formation")
    )
    return jsonify(serializer().outcome(outcome))


@bp.get("/<session_id>/round-results")
def round_results(session_id: str):
    return jsonify(serializer().round_results(services().results.round_results(session_id)))


@bp.get("/<session_id>/playoffs-draw")
def playoffs_draw(session_id: str):
    return jsonify(serializer().playoffs_draw(services().draws.playoffs_draw(session_id)))


@bp.post("/<session_id>/simulate-all")
def simulate_all(session_id: str):
    services().matches.simulate_all(session_id)
    return jsonify(serializer().history(services().results.history(session_id)))


@bp.get("/<session_id>/history")
def history(session_id: str):
    return jsonify(serializer().history(services().results.history(session_id)))
