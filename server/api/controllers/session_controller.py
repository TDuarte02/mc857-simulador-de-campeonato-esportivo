from flask import Blueprint, jsonify

from api.controllers.http import services

bp = Blueprint("session", __name__)


@bp.post("/session")
def create_session():
    session = services().sessions.create()
    return jsonify({"sessionId": session.id}), 201
