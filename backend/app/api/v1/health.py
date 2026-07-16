from flask import Blueprint, current_app

from app.utils.responses import error_response
from app.utils.responses import success_response


health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    try:
        database_status = current_app.config["DATABASE_CHECKER"]()
    except Exception:
        current_app.logger.exception("Database health check failed")
        return error_response(
            "DATABASE_UNAVAILABLE",
            "Database unavailable",
            status_code=503,
        )

    return success_response(
        data={
            "status": "ok",
            "service": "tonglvji-backend",
            "database": database_status,
        },
        message="ok",
    )
