from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.attractions import AttractionError, get_attraction, get_attraction_guide, list_attractions
from app.services.auth import AuthError, get_user_by_identity
from app.utils.responses import error_response, success_response


attractions_bp = Blueprint("attractions", __name__)


def _current_user():
    return get_user_by_identity(get_jwt_identity())


def _parse_pagination_value(name, default):
    if name not in request.args:
        return default
    value = request.args.get(name)
    if value is None or not value.isascii() or not value.isdecimal():
        raise AttractionError("VALIDATION_ERROR", f"{name} must be an integer", 400)
    return int(value)


def _handle_error(error):
    return error_response(error.code, error.message, status_code=error.status_code)


@attractions_bp.get("")
@jwt_required()
def index():
    try:
        _current_user()
        return success_response(
            data=list_attractions(
                city=request.args.get("city"),
                keyword=request.args.get("keyword"),
                limit=_parse_pagination_value("limit", 20),
                offset=_parse_pagination_value("offset", 0),
            ),
            message="ok",
        )
    except (AuthError, AttractionError) as error:
        return _handle_error(error)


@attractions_bp.get("/<int:attraction_id>")
@jwt_required()
def detail(attraction_id):
    try:
        _current_user()
        return success_response(data={"attraction": get_attraction(attraction_id)}, message="ok")
    except (AuthError, AttractionError) as error:
        return _handle_error(error)


@attractions_bp.get("/<int:attraction_id>/guide")
@jwt_required()
def guide(attraction_id):
    try:
        _current_user()
        return success_response(data={"guide": get_attraction_guide(attraction_id)}, message="ok")
    except (AuthError, AttractionError) as error:
        return _handle_error(error)
