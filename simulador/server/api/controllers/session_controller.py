from flask import Blueprint, jsonify, request

from api.controllers.http import optional_str, serializer, services
from api.domain.models import Mode
from api.errors import ValidationError

bp = Blueprint("session", __name__)


@bp.post("/session")
def create_session():
    # The body is optional: without one (or without `mode`) the cup is a full one.
    body = request.get_json(silent=True) if request.content_length else {}
    if not isinstance(body, dict):
        raise ValidationError("INVALID_BODY", "The request body must be a JSON object.")
    mode = optional_str(body, "mode") or Mode.FULL
    if mode not in Mode:
        options = ", ".join(Mode)
        raise ValidationError("INVALID_MODE", f"'mode' must be one of: {options}.")
    session = services().sessions.create(Mode(mode))
    return jsonify({"sessionId": session.id}), 201


@bp.get("/session/<session_id>")
def ret_session_stts(session_id: str):
    session = services().sessions.get(session_id)
    return jsonify({"session": serializer().session(session)})