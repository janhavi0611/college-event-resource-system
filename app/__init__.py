import os

from pathlib import Path

from flask import Flask

from .extensions import db, migrate
from .models import Event, Resource
from .routes.events import events_bp
from .routes.resources import resources_bp
from .routes.requests import requests_bp

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    database_path = Path(app.instance_path) / "app.db"

    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-secret-key"),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    db.init_app(app)
    migrate.init_app(app, db)
    app.register_blueprint(events_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(requests_bp)

    @app.route("/")
    def home():
        return "College Event Resource Allocation System"

    return app