"""AI Business Detective - Flask entry point.   Run:  python app.py"""
import logging

from flask import Flask, jsonify

from config import Config
from src.database.repository import Repository
from src.auth import routes as auth_routes
from src.auth.security import install_security
from src.database.db import init_db
from src.routes import dashboard_routes, data_routes, features_routes, investigation_routes, report_routes, upload_routes


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    for key in ("UPLOAD_FOLDER", "PROCESSED_FOLDER", "REPORT_FOLDER"):
        app.config[key].mkdir(parents=True, exist_ok=True)
    app.repo = Repository(app.config["PROCESSED_FOLDER"], app.config["REPORT_FOLDER"], app.config["DATABASE_URL"])

    init_db(app)
    install_security(app)
    for bp in (auth_routes.bp, features_routes.bp, dashboard_routes.bp, data_routes.bp, upload_routes.bp, investigation_routes.bp, report_routes.bp):
        app.register_blueprint(bp)

    @app.errorhandler(413)
    def too_large(_):
        return jsonify(error="File too large (max 50 MB)."), 413

    logging.basicConfig(filename=str(app.config["BASE_DIR"] / "logs" / "app.log"), level=logging.INFO)
    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=5000)
