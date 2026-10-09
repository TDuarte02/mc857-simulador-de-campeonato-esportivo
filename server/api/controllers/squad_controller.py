from flask import Blueprint, jsonify, request

from api.controllers.http import serializer, services
from api.domain.models import Position
from api.errors import ValidationError

bp = Blueprint("squads", __name__)


@bp.get("/squads")
def list_squads():
    squads = services().squads.list_squads()
    return jsonify({"squads": [serializer().squad(squad) for squad in squads]})


@bp.get("/<squad_id>/players")
def list_players(squad_id: str):
    players = services().squads.list_players(squad_id, _position_filter())
    return jsonify({"players": [serializer().player(player) for player in players]})


@bp.get("/<squad_id>/presets")
def list_presets(squad_id: str):
    presets = services().squads.presets(squad_id)
    return jsonify({"presets": [serializer().preset(preset) for preset in presets]})


def _position_filter() -> Position | None:
    raw = request.args.get("position")
    if raw is None:
        return None
    try:
        return Position(raw.upper())
    except ValueError:
        options = ", ".join(Position)
        raise ValidationError("INVALID_POSITION", f"'position' must be one of: {options}.") from None
