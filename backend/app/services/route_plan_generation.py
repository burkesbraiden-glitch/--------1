from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import Child, ExplorationPlan, Route, RouteDay, RouteStop


class RoutePlanGenerationError(Exception):
    def __init__(self, code, message, status_code):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


MAX_GENERATION_ATTEMPTS = 2


def _validation_error(message):
    raise RoutePlanGenerationError("VALIDATION_ERROR", message, 400)


def _is_positive_integer(value):
    return not isinstance(value, bool) and isinstance(value, int) and value > 0


def _get_owned_route(user, route_id):
    route = Route.query.filter_by(id=route_id, user_id=user.id).first()
    if route is None:
        raise RoutePlanGenerationError("ROUTE_NOT_FOUND", "Route not found", 404)
    if route.status != "ready":
        raise RoutePlanGenerationError("ROUTE_NOT_READY", "Route not ready", 409)
    return route


def _get_owned_child(user, child_id):
    if not _is_positive_integer(child_id):
        _validation_error("child_id must be a positive integer")
    child = Child.query.filter_by(id=child_id, user_id=user.id).first()
    if child is None:
        raise RoutePlanGenerationError("CHILD_NOT_FOUND", "Child not found", 404)
    return child


def _validate_route_stop_ids(route_stop_ids):
    if not isinstance(route_stop_ids, list) or not route_stop_ids:
        _validation_error("route_stop_ids must be a non-empty list")
    if any(not _is_positive_integer(route_stop_id) for route_stop_id in route_stop_ids):
        _validation_error("route_stop_ids must contain positive integers")
    if len(route_stop_ids) != len(set(route_stop_ids)):
        _validation_error("route_stop_ids must not contain duplicates")


def _get_route_stops(route, route_stop_ids):
    stops = (
        RouteStop.query.options(
            joinedload(RouteStop.route_day),
            joinedload(RouteStop.attraction),
        )
        .join(RouteDay)
        .filter(RouteDay.route_id == route.id, RouteStop.id.in_(route_stop_ids))
        .all()
    )
    stops_by_id = {stop.id: stop for stop in stops}
    if len(stops_by_id) != len(route_stop_ids):
        raise RoutePlanGenerationError("ROUTE_STOP_NOT_FOUND", "Route stop not found", 404)
    return [stops_by_id[route_stop_id] for route_stop_id in route_stop_ids]


def _format_date(value):
    return value.isoformat() if value is not None else None


def _build_source_snapshot(route, stop):
    day = stop.route_day
    attraction = stop.attraction
    return {
        "schemaVersion": 1,
        "route": {
            "id": route.id,
            "title": route.title,
            "city": route.city,
            "startDate": _format_date(route.start_date),
            "endDate": _format_date(route.end_date),
        },
        "day": {
            "id": day.id,
            "dayNumber": day.day_number,
            "date": _format_date(day.date),
            "title": day.title,
        },
        "stop": {
            "id": stop.id,
            "sortOrder": stop.sort_order,
            "note": stop.note,
        },
        "attraction": {
            "id": attraction.id,
            "name": attraction.name,
            "city": attraction.city,
            "district": attraction.district,
            "address": attraction.address,
            "summary": attraction.summary,
            "tags": list(attraction.tags or []),
            "recommendedDurationMinutes": attraction.recommended_duration_minutes,
            "coverImage": attraction.cover_image,
        },
    }


def _duration_for_attraction(attraction):
    minutes = attraction.recommended_duration_minutes
    if _is_positive_integer(minutes):
        return f"{minutes}分钟"
    return "按行程安排"


def _build_plan(user, child, route, stop):
    attraction = stop.attraction
    return ExplorationPlan(
        user_id=user.id,
        child_id=child.id,
        route_stop_id=stop.id,
        title=f"{attraction.name}亲子探索",
        destination=attraction.name,
        age_group=child.age_group,
        duration=_duration_for_attraction(attraction),
        interests=list(child.interests or []),
        status="ready",
        source_snapshot=_build_source_snapshot(route, stop),
    )


def _generate_exploration_plans_attempt(user, route_id, child_id, route_stop_ids):
    route = _get_owned_route(user, route_id)
    child = _get_owned_child(user, child_id)
    _validate_route_stop_ids(route_stop_ids)
    stops = _get_route_stops(route, route_stop_ids)

    existing_by_stop_id = {
        plan.route_stop_id: plan
        for plan in ExplorationPlan.query.filter(
            ExplorationPlan.child_id == child.id,
            ExplorationPlan.route_stop_id.in_(route_stop_ids),
        ).all()
    }
    results = []

    for stop in stops:
        plan = existing_by_stop_id.get(stop.id)
        if plan is None:
            plan = _build_plan(user, child, route, stop)
            db.session.add(plan)
            result = "created"
        else:
            result = "existing"
        results.append({"routeStopId": stop.id, "plan": plan, "result": result})
    db.session.commit()

    return {"route": route, "child": child, "results": results}


def generate_exploration_plans_from_route(user, route_id, child_id, route_stop_ids):
    for attempt in range(MAX_GENERATION_ATTEMPTS):
        try:
            return _generate_exploration_plans_attempt(user, route_id, child_id, route_stop_ids)
        except IntegrityError:
            db.session.rollback()
            if attempt + 1 == MAX_GENERATION_ATTEMPTS:
                break
        except SQLAlchemyError:
            db.session.rollback()
            raise RoutePlanGenerationError("DATABASE_ERROR", "Database error", 500)

    raise RoutePlanGenerationError("DATABASE_ERROR", "Database error", 500)
