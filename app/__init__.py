from flask import Flask
from core.tracker import init_db
from app.routes.dashboard import dashboard_bp
from app.routes.profile import profile_bp
from app.routes.brokers import brokers_bp
from app.routes.requests import requests_bp
from app.routes.runner import runner_bp
from app.routes.report import report_bp


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = "incognish-local-secret-change-if-sharing"

    # Init DB on startup
    init_db()

    # Register blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(brokers_bp)
    app.register_blueprint(requests_bp)
    app.register_blueprint(runner_bp)
    app.register_blueprint(report_bp)

    return app
