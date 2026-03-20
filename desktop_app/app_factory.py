from __future__ import annotations

from flask import Flask

from .api import ApiDeps, register_routes


def create_app(deps: ApiDeps) -> Flask:
    app = Flask(__name__)
    register_routes(app, deps)
    return app

