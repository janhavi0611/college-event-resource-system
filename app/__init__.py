import os

from pathlib import Path

from flask import Flask, redirect, url_for

from .extensions import db, migrate
from .models import Event, Resource
from .routes.events import events_bp
from .routes.resources import resources_bp
from .routes.requests import requests_bp
from app.routes.dashboard import dashboard_bp

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
    app.register_blueprint(dashboard_bp)

    @app.route("/")
    def home():
        return redirect(url_for("dashboard.dashboard"))

    @app.errorhandler(404)
    def not_found(_error):
        return "The page you requested was not found.", 404

    @app.errorhandler(500)
    def internal_error(_error):
        db.session.rollback()
        return "Something went wrong. Please try again.", 500

    return app
