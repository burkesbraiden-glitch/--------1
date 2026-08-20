import re
from datetime import date

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Attraction, ExplorationPlan, Route, RouteDay, RouteStop


DEFAULT_LIMIT = 20
MAX_LIMIT = 100
ROUTE_FIELDS = {"title", "city", "startDate", "endDate", "status"}
DAY_FIELDS = {"date", "title"}
STOP_FIELDS = {"attractionId", "note"}


class RouteError(Exception):
    def __init__(self, code, message, status_code, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def _validation_error(message):
    raise RouteError("VALIDATION_ERROR", message, 400)


def _validate_payload(data, allowed_fields, *, required=False):
    if not isinstance(data, dict) or (required and not data) or set(data) - allowed_fields:
        _validation_error("Invalid request data")


def _required_string(data, field_name, max_length):
    value = data.get(field_name)
    if not isinstance(value, str):
        _validation_error(f"{field_name} is required")
    value = value.strip()
    if not 1 <= len(value) <= max_length:
        _validation_error(f"{field_name} must be 1 to {max_length} characters")
    return value


def _optional_string(value, field_name, max_length):
    if value is None:
        return None
    if not isinstance(value, str):
        _validation_error(f"{field_name} must be a string")
    value = value.strip()
    if len(value) > max_length:
        _validation_error(f"{field_name} must be at most {max_length} characters")
    return value


def _parse_optional_date(value, field_name):
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        _validation_error(f"{field_name} must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError:
        _validation_error(f"{field_name} must be YYYY-MM-DD")


def _validate_status(value):
    if not isinstance(value, str) or value not in {"draft", "ready"}:
        _validation_error("status must be draft or ready")
    return value


def _validate_pagination(limit, offset):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
        _validation_error("limit must be an integer from 1 to 100")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        _validation_error("offset must be a non-negative integer")


def _validate_date_range(start_date, end_date):
    if start_date is not None and end_date is not None and end_date < start_date:
        raise RouteError("INVALID_ROUTE_DATE_RANGE", "endDate must not be before startDate", 400)


def _validate_day_date(route, day_date):
    if (
        day_date is not None
        and route.start_date is not None
        and route.end_date is not None
        and not route.start_date <= day_date <= route.end_date
    ):
        raise RouteError("ROUTE_DAY_DATE_OUT_OF_RANGE", "Route day date is outside route range", 400)


def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise RouteError("DATABASE_ERROR", "Database error", 500)


def _get_route(user_id, route_id):
    route = Route.query.filter_by(id=route_id, user_id=user_id).first()
    if route is None:
        raise RouteError("ROUTE_NOT_FOUND", "Route not found", 404)
    return route


def _get_route_day(route, day_id):
    day = RouteDay.query.filter_by(id=day_id, route_id=route.id).first()
    if day is None:
        raise RouteError("ROUTE_DAY_NOT_FOUND", "Route day not found", 404)
    return day


def _get_route_stop(day, stop_id):
    stop = RouteStop.query.filter_by(id=stop_id, route_day_id=day.id).first()
    if stop is None:
        raise RouteError("ROUTE_STOP_NOT_FOUND", "Route stop not found", 404)
    return stop


def _stop_has_exploration_plans(stop_id):
    return ExplorationPlan.query.filter_by(route_stop_id=stop_id).first() is not None


def _day_has_exploration_plans(day_id):
    return (
        ExplorationPlan.query.join(
            RouteStop, ExplorationPlan.route_stop_id == RouteStop.id
        )
        .filter(RouteStop.route_day_id == day_id)
        .first()
        is not None
    )


def _route_has_exploration_plans(route_id):
    return (
        ExplorationPlan.query.join(
            RouteStop, ExplorationPlan.route_stop_id == RouteStop.id
        )
        .join(RouteDay, RouteStop.route_day_id == RouteDay.id)
        .filter(RouteDay.route_id == route_id)
        .first()
        is not None
    )


def _next_value(model, field, parent_field, parent_id):
    return (db.session.query(db.func.max(field)).filter(parent_field == parent_id).scalar() or 0) + 1


def _sqlite_next_id(model):
    if db.engine.dialect.name != "sqlite":
        return None
    return (db.session.query(db.func.max(model.id)).scalar() or 0) + 1


def _resequence_days(route_id):
    days = (
        RouteDay.query.filter_by(route_id=route_id)
        .order_by(RouteDay.day_number.asc(), RouteDay.id.asc())
        .all()
    )
    if not days:
        return
    temporary_start = max(day.day_number for day in days) + len(days) + 1
    for index, day in enumerate(days):
        day.day_number = temporary_start + index
    db.session.flush()
    for index, day in enumerate(days, start=1):
        day.day_number = index


def _resequence_stops(day_id):
    stops = (
        RouteStop.query.filter_by(route_day_id=day_id)
        .order_by(RouteStop.sort_order.asc(), RouteStop.id.asc())
        .all()
    )
    if not stops:
        return
    temporary_start = max(stop.sort_order for stop in stops) + len(stops) + 1
    for index, stop in enumerate(stops):
        stop.sort_order = temporary_start + index
    db.session.flush()
    for index, stop in enumerate(stops, start=1):
        stop.sort_order = index


def _route_has_city_conflict(route_id, city):
    return (
        RouteStop.query.join(RouteDay)
        .join(Attraction)
        .filter(RouteDay.route_id == route_id, Attraction.city != city)
        .first()
        is not None
    )


def _validate_existing_day_dates(route, start_date, end_date):
    if start_date is None or end_date is None:
        return
    day_outside_range = (
        RouteDay.query.filter(
            RouteDay.route_id == route.id,
            RouteDay.date.isnot(None),
            (RouteDay.date < start_date) | (RouteDay.date > end_date),
        )
        .first()
    )
    if day_outside_range is not None:
        raise RouteError("ROUTE_DAY_DATE_OUT_OF_RANGE", "Route day date is outside route range", 400)


def list_routes(user_id, limit=DEFAULT_LIMIT, offset=0):
    _validate_pagination(limit, offset)
    query = Route.query.filter_by(user_id=user_id)
    return {
        "items": query.order_by(Route.updated_at.desc(), Route.id.desc()).limit(limit).offset(offset).all(),
        "total": query.count(),
        "limit": limit,
        "offset": offset,
    }


def get_route(user_id, route_id):
    return _get_route(user_id, route_id)


def create_route(user_id, data):
    _validate_payload(data, ROUTE_FIELDS)
    title = _required_string(data, "title", 120)
    city = _required_string(data, "city", 80)
    start_date = _parse_optional_date(data.get("startDate"), "startDate")
    end_date = _parse_optional_date(data.get("endDate"), "endDate")
    _validate_date_range(start_date, end_date)
    status = "draft" if "status" not in data else _validate_status(data["status"])

    route = Route(
        id=_sqlite_next_id(Route),
        user_id=user_id,
        title=title,
        city=city,
        start_date=start_date,
        end_date=end_date,
        status=status,
    )
    db.session.add(route)
    _commit()
    return route


def update_route(user_id, route_id, data):
    route = _get_route(user_id, route_id)
    _validate_payload(data, ROUTE_FIELDS, required=True)
    title = _required_string(data, "title", 120) if "title" in data else route.title
    city = _required_string(data, "city", 80) if "city" in data else route.city
    start_date = _parse_optional_date(data["startDate"], "startDate") if "startDate" in data else route.start_date
    end_date = _parse_optional_date(data["endDate"], "endDate") if "endDate" in data else route.end_date
    status = _validate_status(data["status"]) if "status" in data else None
    _validate_date_range(start_date, end_date)
    _validate_existing_day_dates(route, start_date, end_date)
    if city != route.city and _route_has_city_conflict(route.id, city):
        raise RouteError("ROUTE_CITY_CONFLICT", "Route city conflicts with existing stops", 400)

    route.title = title
    route.city = city
    route.start_date = start_date
    route.end_date = end_date
    structure_changed = any(field in data for field in {"title", "city", "startDate", "endDate"})
    if status is not None:
        route.status = status
    elif route.status == "ready" and structure_changed:
        route.status = "draft"
    _commit()
    return route


def delete_route(user_id, route_id):
    route = _get_route(user_id, route_id)
    if _route_has_exploration_plans(route.id):
        raise RouteError("ROUTE_HAS_EXPLORATION_PLANS", "Route has exploration plans", 409)
    db.session.delete(route)
    _commit()


def create_route_day(user_id, route_id, data):
    route = _get_route(user_id, route_id)
    _validate_payload(data, DAY_FIELDS)
    day_date = _parse_optional_date(data.get("date"), "date")
    _validate_day_date(route, day_date)
    title = _optional_string(data.get("title"), "title", 120)
    day = RouteDay(
        id=_sqlite_next_id(RouteDay),
        route_id=route.id,
        day_number=_next_value(RouteDay, RouteDay.day_number, RouteDay.route_id, route.id),
        date=day_date,
        title=title,
    )
    route.status = "draft"
    db.session.add(day)
    _commit()
    return day


def update_route_day(user_id, route_id, day_id, data):
    route = _get_route(user_id, route_id)
    day = _get_route_day(route, day_id)
    _validate_payload(data, DAY_FIELDS, required=True)
    day_date = _parse_optional_date(data["date"], "date") if "date" in data else day.date
    _validate_day_date(route, day_date)
    if "date" in data:
        day.date = day_date
    if "title" in data:
        day.title = _optional_string(data["title"], "title", 120)
    route.status = "draft"
    _commit()
    return day


def delete_route_day(user_id, route_id, day_id):
    route = _get_route(user_id, route_id)
    day = _get_route_day(route, day_id)
    if _day_has_exploration_plans(day.id):
        raise RouteError("ROUTE_DAY_HAS_EXPLORATION_PLANS", "Route day has exploration plans", 409)
    db.session.delete(day)
    db.session.flush()
    _resequence_days(route.id)
    route.status = "draft"
    _commit()


def _get_active_attraction(attraction_id):
    if isinstance(attraction_id, bool) or not isinstance(attraction_id, int) or attraction_id <= 0:
        _validation_error("attractionId must be a positive integer")
    attraction = Attraction.query.filter_by(id=attraction_id, is_active=True).first()
    if attraction is None:
        raise RouteError("ATTRACTION_NOT_FOUND", "Attraction not found", 404)
    return attraction


def _optional_note(value):
    if value is None:
        return None
    if not isinstance(value, str):
        _validation_error("note must be a string")
    return value.strip()


def create_route_stop(user_id, route_id, day_id, data):
    route = _get_route(user_id, route_id)
    day = _get_route_day(route, day_id)
    _validate_payload(data, STOP_FIELDS)
    if "attractionId" not in data:
        _validation_error("attractionId is required")
    attraction = _get_active_attraction(data["attractionId"])
    if attraction.city != route.city:
        raise RouteError("ATTRACTION_CITY_MISMATCH", "Attraction city does not match route city", 400)
    note = _optional_note(data.get("note"))
    stop = RouteStop(
        id=_sqlite_next_id(RouteStop),
        route_day_id=day.id,
        attraction_id=attraction.id,
        sort_order=_next_value(RouteStop, RouteStop.sort_order, RouteStop.route_day_id, day.id),
        note=note,
    )
    route.status = "draft"
    db.session.add(stop)
    _commit()
    return stop


def update_route_stop(user_id, route_id, day_id, stop_id, data):
    route = _get_route(user_id, route_id)
    day = _get_route_day(route, day_id)
    stop = _get_route_stop(day, stop_id)
    _validate_payload(data, {"note"}, required=True)
    stop.note = _optional_note(data["note"])
    route.status = "draft"
    _commit()
    return stop


def delete_route_stop(user_id, route_id, day_id, stop_id):
    route = _get_route(user_id, route_id)
    day = _get_route_day(route, day_id)
    stop = _get_route_stop(day, stop_id)
    if _stop_has_exploration_plans(stop.id):
        raise RouteError(
            "ROUTE_STOP_HAS_EXPLORATION_PLANS",
            "Route stop has exploration plans",
            409,
        )
    db.session.delete(stop)
    db.session.flush()
    _resequence_stops(day.id)
    route.status = "draft"
    _commit()


def _validate_exact_order_ids(ids, current_ids, code, message):
    if (
        not isinstance(ids, list)
        or any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in ids)
        or len(ids) != len(set(ids))
        or set(ids) != set(current_ids)
    ):
        raise RouteError(code, message, 400)


def _apply_collision_safe_order(items, position_name, ordered_ids):
    if not items:
        return
    by_id = {item.id: item for item in items}
    temporary_base = max(getattr(item, position_name) for item in items) + len(items) + 1000
    for index, item in enumerate(items):
        setattr(item, position_name, temporary_base + index)
    db.session.flush()
    for index, item_id in enumerate(ordered_ids, start=1):
        setattr(by_id[item_id], position_name, index)


def reorder_route_days(user_id, route_id, day_ids):
    route = _get_route(user_id, route_id)
    days = (
        RouteDay.query.filter_by(route_id=route.id)
        .order_by(RouteDay.day_number.asc(), RouteDay.id.asc())
        .with_for_update()
        .all()
    )
    _validate_exact_order_ids(
        day_ids,
        [day.id for day in days],
        "INVALID_ROUTE_DAY_ORDER",
        "dayIds must contain every route day exactly once",
    )
    _apply_collision_safe_order(days, "day_number", day_ids)
    if days:
        route.status = "draft"
    _commit()
    return route


def reorder_route_stops(user_id, route_id, day_id, stop_ids):
    route = _get_route(user_id, route_id)
    day = _get_route_day(route, day_id)
    stops = (
        RouteStop.query.filter_by(route_day_id=day.id)
        .order_by(RouteStop.sort_order.asc(), RouteStop.id.asc())
        .with_for_update()
        .all()
    )
    _validate_exact_order_ids(
        stop_ids,
        [stop.id for stop in stops],
        "INVALID_ROUTE_STOP_ORDER",
        "stopIds must contain every route stop exactly once",
    )
    _apply_collision_safe_order(stops, "sort_order", stop_ids)
    if stops:
        route.status = "draft"
    _commit()
    return route


def _format_datetime(value):
    if value is None:
        return None
    return f"{value.isoformat()}Z"


def serialize_route_summary(route):
    return {
        "id": route.id,
        "title": route.title,
        "city": route.city,
        "startDate": route.start_date.isoformat() if route.start_date is not None else None,
        "endDate": route.end_date.isoformat() if route.end_date is not None else None,
        "status": route.status,
        "createdAt": _format_datetime(route.created_at),
        "updatedAt": _format_datetime(route.updated_at),
    }


def serialize_route_stop_attraction(attraction):
    return {
        "id": attraction.id,
        "name": attraction.name,
        "city": attraction.city,
        "district": attraction.district,
        "summary": attraction.summary,
        "recommendedDurationMinutes": attraction.recommended_duration_minutes,
        "coverImage": attraction.cover_image,
    }


def serialize_route_stop(stop):
    return {
        "id": stop.id,
        "sortOrder": stop.sort_order,
        "note": stop.note,
        "attraction": serialize_route_stop_attraction(stop.attraction),
    }


def serialize_route_day(day):
    stops = sorted(day.stops, key=lambda stop: (stop.sort_order, stop.id))
    return {
        "id": day.id,
        "dayNumber": day.day_number,
        "date": day.date.isoformat() if day.date is not None else None,
        "title": day.title,
        "stops": [serialize_route_stop(stop) for stop in stops],
    }


def serialize_route_detail(route):
    payload = serialize_route_summary(route)
    days = sorted(route.days, key=lambda day: (day.day_number, day.id))
    payload["days"] = [serialize_route_day(day) for day in days]
    return payload
