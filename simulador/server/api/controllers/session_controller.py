from flask import Blueprint, jsonify

from api.controllers.http import serializer, services

bp = Blueprint("session", __name__)


@bp.post("/session")
def create_session():
    session = services().sessions.create()
    return jsonify({"sessionId": session.id}), 201

@bp.get("/session/<session_id>")
def ret_session_stts(session_id: str):
    session = services().sessions.get(session_id)
    return jsonify({"session": serializer().session(session)})