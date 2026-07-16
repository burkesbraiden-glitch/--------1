from flask import Blueprint

from app.api.v1.auth import auth_bp
from app.api.v1.children import children_bp
from app.api.v1.guides import guides_bp
from app.api.v1.health import health_bp
from app.api.v1.plans import plans_bp
from app.api.v1.tasks import tasks_bp


v1_bp = Blueprint("v1", __name__)
v1_bp.register_blueprint(auth_bp, url_prefix="/auth")
v1_bp.register_blueprint(children_bp, url_prefix="/children")
v1_bp.register_blueprint(plans_bp, url_prefix="/plans")
v1_bp.register_blueprint(guides_bp, url_prefix="/plans")
v1_bp.register_blueprint(tasks_bp, url_prefix="/plans")
v1_bp.register_blueprint(health_bp)
