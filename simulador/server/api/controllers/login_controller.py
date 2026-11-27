from flask import Blueprint, jsonify, request

from api.controllers.http import serializer, services
from api.errors import NotFoundError

bp = Blueprint("login", __name__)

@bp.post("/register")
def register():
    info = request.get_json(silent=True) or {}
    if not info or "email" not in info or "password" not in info:
        return jsonify({"error": "INSUFFICIENT_INFO"}), 400
    if services().login.exists(email=info["email"]):
        return jsonify({"error": "USER_ALREADY_EXISTS"}), 409
    
    session_id: str
    if "sessionId" in info and info["sessionId"]:
        session_obj = services().sessions.get(info["sessionId"])
        session_id = session_obj.id
    else:
        session_id = services().sessions.create().id
    user = services().login.reg_user(info["email"], info["password"], session_id)
    return jsonify({"user": serializer().user(user)}), 201


@bp.post("/login")
def login():
    info = request.get_json(silent=True) or {}
    if not info or "email" not in info or "password" not in info:
        return jsonify({"error": "INSUFFICIENT_INFO"}), 400
    
    email = info["email"]
    password = info["password"]
    try:
        user = services().login.auth(email=email, password=password)
    except (NotFoundError, ValueError):
        return jsonify({"error": "INVALID_CREDENTIALS"}), 401
    return jsonify({"user": serializer().user(user)}), 200
