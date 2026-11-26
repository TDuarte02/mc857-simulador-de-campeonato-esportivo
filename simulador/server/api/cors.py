"""CORS headers, so the web build of the app can call the API from the browser."""

import re

from flask import Flask, request

# The API has no authentication, so only pages served from this machine are
# allowed unless CORS_ORIGINS names others.
_LOCAL_ORIGIN = re.compile(r"http://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?")


def register_cors(app: Flask, extra_origins: tuple[str, ...] = ()) -> None:
    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        if origin and (_LOCAL_ORIGIN.fullmatch(origin) or origin in extra_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.vary.add("Origin")
        return response
