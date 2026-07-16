from flask import Blueprint, current_app, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.auth import (
    AuthError,
    get_user_by_identity,
    login_with_mock_wechat,
    login_with_phone,
    send_verification_code,
    serialize_user,
)
from app.utils.responses import error_response, success_response


auth_bp = Blueprint("auth", __name__)


def get_json_object():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise AuthError("VALIDATION_ERROR", "Request body must be a JSON object", 400)
    return payload


def handle_auth_error(error):
    return error_response(error.code, error.message, status_code=error.status_code)


@auth_bp.post("/send-code")
def send_code():
    try:
        payload = get_json_object()
        data = send_verification_code(payload, current_app.config)
        return success_response(data=data, message="Verification code sent")
    except AuthError as error:
        return handle_auth_error(error)


@auth_bp.post("/login")
def login():
    try:
        payload = get_json_object()
        data = login_with_phone(payload, current_app.config)
        return success_response(data=data, message="ok")
    except AuthError as error:
        return handle_auth_error(error)


@auth_bp.post("/mock-wechat-login")
def mock_wechat_login():
    try:
        payload = request.get_json(silent=True)
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            raise AuthError("VALIDATION_ERROR", "Request body must be a JSON object", 400)
        data = login_with_mock_wechat(payload, current_app.config)
        return success_response(data=data, message="ok")
    except AuthError as error:
        return handle_auth_error(error)


@auth_bp.get("/me")
@jwt_required()
def me():
    try:
        user = get_user_by_identity(get_jwt_identity())
        return success_response(data={"user": serialize_user(user)}, message="ok")
    except AuthError as error:
        return handle_auth_error(error)


@auth_bp.post("/logout")
@jwt_required()
def logout():
    return success_response(data={"loggedOut": True}, message="Logged out")
