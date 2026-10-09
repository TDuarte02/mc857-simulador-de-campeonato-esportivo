from flask import Flask

from api.config import Settings
from api.container import Container, build_container
from api.controllers import session_controller, squad_controller, tournament_controller
from api.controllers.serializers import Serializer
from api.errors import register_error_handlers


def create_app(container: Container | None = None) -> Flask:
    app = Flask(__name__)
    app.json.sort_keys = False
    app.json.ensure_ascii = False

    container = container or build_container(Settings.from_env())
    app.extensions["container"] = container
    app.extensions["serializer"] = Serializer(container.squads)

    for controller in (session_controller, squad_controller, tournament_controller):
        app.register_blueprint(controller.bp)
    register_error_handlers(app)
    return app
