from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.auth import AuthError, get_user_by_identity
from app.services.children import (
    ChildError,
    create_child,
    get_child_for_user,
    list_children,
    update_child,
)
from app.utils.responses import error_response, success_response


children_bp = Blueprint("children", __name__)


def get_json_object():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ChildError("VALIDATION_ERROR", "Request body must be a JSON object", 400)
    return payload


def current_user():
    return get_user_by_identity(get_jwt_identity())


def handle_error(error):
    return error_response(error.code, error.message, status_code=error.status_code)


@children_bp.get("")
@jwt_required()
def index():
    try:
        data = list_children(current_user())
        return success_response(data=data, message="ok")
    except (AuthError, ChildError) as error:
        return handle_error(error)


@children_bp.post("")
@jwt_required()
def create():
    try:
        child = create_child(current_user(), get_json_object())
        return success_response(data={"child": child}, message="Child created", status_code=201)
    except (AuthError, ChildError) as error:
        return handle_error(error)


@children_bp.get("/<int:child_id>")
@jwt_required()
def detail(child_id):
    try:
        child = get_child_for_user(current_user(), child_id)
        return success_response(data={"child": child}, message="ok")
    except (AuthError, ChildError) as error:
        return handle_error(error)


@children_bp.patch("/<int:child_id>")
@jwt_required()
def patch(child_id):
    try:
        child = update_child(current_user(), child_id, get_json_object())
        return success_response(data={"child": child}, message="ok")
    except (AuthError, ChildError) as error:
        return handle_error(error)
