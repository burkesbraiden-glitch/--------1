from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.auth import AuthError, get_user_by_identity
from app.services.plans import (
    PlanError,
    create_plan,
    get_plan,
    list_plans,
    start_plan,
    update_plan,
)
from app.utils.responses import error_response, success_response


plans_bp = Blueprint("plans", __name__)


def get_json_object():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise PlanError("VALIDATION_ERROR", "Request body must be a JSON object", 400)
    return payload


def current_user():
    return get_user_by_identity(get_jwt_identity())


def handle_error(error):
    return error_response(error.code, error.message, status_code=error.status_code)


@plans_bp.post("")
@jwt_required()
def create():
    try:
        plan = create_plan(current_user(), get_json_object())
        return success_response(data={"plan": plan}, message="Plan created", status_code=201)
    except (AuthError, PlanError) as error:
        return handle_error(error)


@plans_bp.get("")
@jwt_required()
def index():
    try:
        return success_response(data=list_plans(current_user()), message="ok")
    except (AuthError, PlanError) as error:
        return handle_error(error)


@plans_bp.get("/<int:plan_id>")
@jwt_required()
def detail(plan_id):
    try:
        return success_response(data={"plan": get_plan(current_user(), plan_id)}, message="ok")
    except (AuthError, PlanError) as error:
        return handle_error(error)


@plans_bp.patch("/<int:plan_id>")
@jwt_required()
def patch(plan_id):
    try:
        plan = update_plan(current_user(), plan_id, get_json_object())
        return success_response(data={"plan": plan}, message="ok")
    except (AuthError, PlanError) as error:
        return handle_error(error)


@plans_bp.post("/<int:plan_id>/start")
@jwt_required()
def start(plan_id):
    try:
        plan = start_plan(current_user(), plan_id)
        return success_response(data={"plan": plan}, message="Exploration started")
    except (AuthError, PlanError) as error:
        return handle_error(error)
