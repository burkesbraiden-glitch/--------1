from flask import Blueprint
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.account import AccountError, delete_account, export_account
from app.services.auth import AuthError, get_user_by_identity
from app.utils.responses import error_response, success_response


account_bp = Blueprint("account", __name__)


def _current_user():
    return get_user_by_identity(get_jwt_identity())


def _handle_error(error):
    return error_response(error.code, error.message, status_code=error.status_code)


@account_bp.get("/export")
@jwt_required()
def export():
    try:
        return success_response(data={"export": export_account(_current_user())}, message="Account export ready")
    except (AuthError, AccountError) as error:
        return _handle_error(error)


@account_bp.delete("")
@jwt_required()
def delete():
    try:
        return success_response(data=delete_account(_current_user()), message="Account deleted")
    except (AuthError, AccountError) as error:
        return _handle_error(error)
