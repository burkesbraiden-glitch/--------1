from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.auth import AuthError, get_user_by_identity
from app.services.routes import (
    RouteError,
    create_route,
    create_route_day,
    create_route_stop,
    delete_route,
    delete_route_day,
    delete_route_stop,
    get_route,
    list_routes,
    reorder_route_days,
    reorder_route_stops,
    serialize_route_detail,
    serialize_route_summary,
    update_route,
    update_route_day,
    update_route_stop,
)
from app.utils.responses import error_response, success_response


routes_bp = Blueprint("routes", __name__)


def _current_user_id():
    return get_user_by_identity(get_jwt_identity()).id


def _json_object():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise RouteError("VALIDATION_ERROR", "Request body must be a JSON object", 400)
    return payload


def _pagination_value(name, default):
    if name not in request.args:
        return default
    value = request.args.get(name)
    if value is None or not value.isascii() or not value.isdecimal():
        raise RouteError("VALIDATION_ERROR", f"{name} must be an integer", 400)
    return int(value)


def _handle_error(error):
    return error_response(
        error.code,
        error.message,
        details=getattr(error, "details", None),
        status_code=error.status_code,
    )


def _route_response(route, *, message="ok", status_code=200):
    return success_response(data={"route": serialize_route_detail(route)}, message=message, status_code=status_code)


@routes_bp.get("")
@jwt_required()
def index():
    try:
        data = list_routes(
            _current_user_id(),
            limit=_pagination_value("limit", 20),
            offset=_pagination_value("offset", 0),
        )
        return success_response(
            data={
                "items": [serialize_route_summary(route) for route in data["items"]],
                "total": data["total"],
                "limit": data["limit"],
                "offset": data["offset"],
            },
            message="ok",
        )
    except (AuthError, RouteError) as error:
        return _handle_error(error)


@routes_bp.post("")
@jwt_required()
def create():
    try:
        return _route_response(create_route(_current_user_id(), _json_object()), message="Route created", status_code=201)
    except (AuthError, RouteError) as error:
        return _handle_error(error)


@routes_bp.get("/<int:route_id>")
@jwt_required()
def detail(route_id):
    try:
        return _route_response(get_route(_current_user_id(), route_id))
    except (AuthError, RouteError) as error:
        return _handle_error(error)


@routes_bp.patch("/<int:route_id>")
@jwt_required()
def patch(route_id):
    try:
        return _route_response(update_route(_current_user_id(), route_id, _json_object()))
    except (AuthError, RouteError) as error:
        return _handle_error(error)


@routes_bp.delete("/<int:route_id>")
@jwt_required()
def delete(route_id):
    try:
        delete_route(_current_user_id(), route_id)
        return success_response(data=None, message="Route deleted")
    except (AuthError, RouteError) as error:
        return _handle_error(error)


@routes_bp.post("/<int:route_id>/days")
@jwt_required()
def create_day(route_id):
    try:
        user_id = _current_user_id()
        create_route_day(user_id, route_id, _json_object())
        return _route_response(get_route(user_id, route_id), message="Route day created", status_code=201)
    except (AuthError, RouteError) as error:
        return _handle_error(error)


@routes_bp.patch("/<int:route_id>/days/reorder")
@jwt_required()
def reorder_days(route_id):
    try:
        payload = _json_object()
        if "dayIds" not in payload:
            raise RouteError("VALIDATION_ERROR", "dayIds is required", 400)
        return _route_response(reorder_route_days(_current_user_id(), route_id, payload["dayIds"]))
    except (AuthError, RouteError) as error:
        return _handle_error(error)


@routes_bp.patch("/<int:route_id>/days/<int:day_id>")
@jwt_required()
def patch_day(route_id, day_id):
    try:
        user_id = _current_user_id()
        update_route_day(user_id, route_id, day_id, _json_object())
        return _route_response(get_route(user_id, route_id))
    except (AuthError, RouteError) as error:
        return _handle_error(error)


@routes_bp.delete("/<int:route_id>/days/<int:day_id>")
@jwt_required()
def delete_day(route_id, day_id):
    try:
        user_id = _current_user_id()
        delete_route_day(user_id, route_id, day_id)
        return _route_response(get_route(user_id, route_id))
    except (AuthError, RouteError) as error:
        return _handle_error(error)


@routes_bp.post("/<int:route_id>/days/<int:day_id>/stops")
@jwt_required()
def create_stop(route_id, day_id):
    try:
        user_id = _current_user_id()
        create_route_stop(user_id, route_id, day_id, _json_object())
        return _route_response(get_route(user_id, route_id), message="Route stop created", status_code=201)
    except (AuthError, RouteError) as error:
        return _handle_error(error)


@routes_bp.patch("/<int:route_id>/days/<int:day_id>/stops/reorder")
@jwt_required()
def reorder_stops(route_id, day_id):
    try:
        payload = _json_object()
        if "stopIds" not in payload:
            raise RouteError("VALIDATION_ERROR", "stopIds is required", 400)
        return _route_response(reorder_route_stops(_current_user_id(), route_id, day_id, payload["stopIds"]))
    except (AuthError, RouteError) as error:
        return _handle_error(error)


@routes_bp.patch("/<int:route_id>/days/<int:day_id>/stops/<int:stop_id>")
@jwt_required()
def patch_stop(route_id, day_id, stop_id):
    try:
        user_id = _current_user_id()
        update_route_stop(user_id, route_id, day_id, stop_id, _json_object())
        return _route_response(get_route(user_id, route_id))
    except (AuthError, RouteError) as error:
        return _handle_error(error)


@routes_bp.delete("/<int:route_id>/days/<int:day_id>/stops/<int:stop_id>")
@jwt_required()
def delete_stop(route_id, day_id, stop_id):
    try:
        user_id = _current_user_id()
        delete_route_stop(user_id, route_id, day_id, stop_id)
        return _route_response(get_route(user_id, route_id))
    except (AuthError, RouteError) as error:
        return _handle_error(error)
