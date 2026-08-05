from importlib import import_module
import os

from flask import Flask
from werkzeug.exceptions import HTTPException

from app.api.v1 import v1_bp
from app.config import config_by_env, validate_production_config
from app.extensions import cors, db, jwt, migrate
from app.services.database import check_database_connection
from app.utils.responses import error_response


def create_app(config_name=None, database_checker=None):
    app = Flask(__name__)

    env_name = config_name if config_name is not None else os.getenv("APP_ENV", "development")
    if env_name not in config_by_env:
        raise RuntimeError("Invalid application environment")

    app.config.from_object(config_by_env[env_name])
    validate_production_config(app.config)
    app.config["DATABASE_CHECKER"] = database_checker or check_database_connection

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, origins=app.config["CORS_ORIGINS"])

    import_module("app.models")

    app.register_blueprint(v1_bp, url_prefix="/api/v1")
    register_error_handlers(app)
    register_jwt_handlers(jwt)

    return app


def register_error_handlers(app):
    @app.errorhandler(404)
    def handle_not_found(error):
        return error_response("NOT_FOUND", "Resource not found", status_code=404)

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return error_response(
            "METHOD_NOT_ALLOWED",
            "Method not allowed",
            status_code=405,
        )

    @app.errorhandler(500)
    def handle_internal_error(error):
        return error_response("INTERNAL_SERVER_ERROR", "Internal server error", status_code=500)

    @app.errorhandler(Exception)
    def handle_exception(error):
        if isinstance(error, HTTPException):
            return error
        app.logger.exception("Unhandled exception: %s", error)
        return error_response("INTERNAL_SERVER_ERROR", "Internal server error", status_code=500)


def register_jwt_handlers(jwt_manager):
    @jwt_manager.unauthorized_loader
    def handle_missing_token(error):
        return error_response("UNAUTHORIZED", "Authorization required", status_code=401)

    @jwt_manager.invalid_token_loader
    def handle_invalid_token(error):
        return error_response("INVALID_TOKEN", "Invalid token", status_code=401)

    @jwt_manager.expired_token_loader
    def handle_expired_token(jwt_header, jwt_payload):
        return error_response("TOKEN_EXPIRED", "Token expired", status_code=401)

    @jwt_manager.needs_fresh_token_loader
    def handle_needs_fresh_token(jwt_header, jwt_payload):
        return error_response("INVALID_TOKEN", "Invalid token", status_code=401)

    @jwt_manager.revoked_token_loader
    def handle_revoked_token(jwt_header, jwt_payload):
        return error_response("INVALID_TOKEN", "Invalid token", status_code=401)
