"""Helpers shared by the controllers: access to the services and request parsing."""

from flask import current_app, request

from api.container import Container
from api.controllers.serializers import Serializer
from api.errors import ValidationError


def services() -> Container:
    return current_app.extensions["container"]


def serializer() -> Serializer:
    return current_app.extensions["serializer"]


def json_body() -> dict:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValidationError("INVALID_BODY", "The request body must be a JSON object.")
    return body


def require_str(body: dict, key: str) -> str:
    value = body.get(key)
    if not isinstance(value, str) or not value:
        raise ValidationError("INVALID_BODY", f"'{key}' must be a non-empty string.")
    return value


def optional_str(body: dict, key: str) -> str | None:
    value = body.get(key)
    if value is not None and not isinstance(value, str):
        raise ValidationError("INVALID_BODY", f"'{key}' must be a string.")
    return value


def require_id_list(body: dict, key: str) -> list[int]:
    value = body.get(key)
    # bool is a subclass of int, so it is ruled out explicitly.
    if not isinstance(value, list) or any(type(item) is not int for item in value):
        raise ValidationError("INVALID_BODY", f"'{key}' must be a list of player ids.")
    return value
