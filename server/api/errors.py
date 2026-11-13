from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    status = 400

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class ValidationError(ApiError):
    status = 400


class NotFoundError(ApiError):
    status = 404


class ConflictError(ApiError):
    """The request is valid but the session is not in a state that allows it."""

    status = 409


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        return jsonify({"error": {"code": error.code, "message": error.message}}), error.status

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        code = (error.name or "error").upper().replace(" ", "_")
        return jsonify({"error": {"code": code, "message": error.description}}), error.code
