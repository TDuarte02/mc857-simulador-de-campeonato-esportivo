from flask import Blueprint, jsonify

from api.controllers.http import json_body, serializer, services
from api.errors import ConflictError, ValidationError

bp = Blueprint("login", __name__)


def _credentials(body: dict) -> tuple[str, str]:
    """`email` and `password`, both non-empty strings."""
    email, password = body.get("email"), body.get("password")
    if not isinstance(email, str) or not email.strip() or not isinstance(password, str) or not password:
        raise ValidationError("INSUFFICIENT_INFO", "'email' and 'password' must be non-empty strings.")
    return email, password


@bp.post("/register")
def register():
    body = json_body()
    email, password = _credentials(body)
    if "@" not in email.strip()[1:-1]:  # something before and after the @
        raise ValidationError("INVALID_EMAIL", "'email' is not an email address.")
    session_id = body.get("sessionId")
    if session_id is not None and not isinstance(session_id, str):
        raise ValidationError("INVALID_BODY", "'sessionId' must be a string.")
    # Checked first so a taken email doesn't create a session for nothing. Two
    # registrations racing past this check are still safe: the repository refuses the
    # second one, and LoginService turns that into the same 409.
    if services().login.exists(email):
        raise ConflictError("USER_ALREADY_EXISTS", "An account with this email already exists.")

    if session_id:
        session_id = services().sessions.get(session_id).id  # 404 / 409 when it can't be used
    else:
        session_id = services().sessions.create().id
    user = services().login.reg_user(email, password, session_id)
    return jsonify({"user": serializer().user(user)}), 201


@bp.post("/login")
def login():
    email, password = _credentials(json_body())
    user = services().login.auth(email=email, password=password)  # 401 when wrong
    return jsonify({"user": serializer().user(user)}), 200
