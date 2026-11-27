from flask import Blueprint, jsonify

from api.controllers.http import services

bp = Blueprint("meta", __name__)


@bp.get("/meta")
def meta():
    """What runs behind the API, for operators and the functional tests."""
    info = services().meta
    return jsonify({"simulator": info.simulator, "catalogVersion": info.catalog_version})
