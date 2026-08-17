from datetime import date, datetime
from importlib import import_module

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import event

from app.extensions import db
from app.models import Attraction, Route, RouteDay, RouteStop, User


def route_service():
    return import_module("app.services.routes")


@pytest.fixture()
def route_service_db(app):
    def enable_foreign_keys(dbapi_connection, _connection_record):
        if dbapi_connection.__class__.__module__.startswith("sqlite3"):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

    with app.app_context():
        event.listen(db.engine, "connect", enable_foreign_keys)
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()
        event.remove(db.engine, "connect", enable_foreign_keys)


def add_user(user_id):
    user = User(id=user_id, phone=f"1390000{user_id:04d}", nickname=f"家长{user_id}")
    db.session.add(user)
    db.session.commit()
    return user


def add_attraction(attraction_id, *, city="北京", is_active=True):
    attraction = Attraction(
        id=attraction_id,
        name=f"景点{attraction_id}",
        city=city,
        summary="适合亲子观察的文化景点。",
        tags=["历史"],
        is_active=is_active,
    )
    db.session.add(attraction)
    db.session.commit()
    return attraction


def create_route(user_id=1, **data):
    values = {"title": "北京探索", "city": "北京"}
    values.update(data)
    return route_service().create_route(user_id, values)


def assert_error(callback, code, status=400):
    service = route_service()
    with pytest.raises(service.RouteError) as error:
        callback(service)
    assert error.value.code == code
    assert error.value.status_code == status


def test_create_route_normalizes_text_defaults_draft_and_accepts_ready(app, route_service_db):
    with app.app_context():
        add_user(1)
        route = create_route(title=" 北京探索 ", city=" 北京 ")
        ready = create_route(title="广州探索", city="广州", status="ready")

        assert (route.title, route.city, route.status) == ("北京探索", "北京", "draft")
        assert ready.status == "ready"


@pytest.mark.parametrize(
    "data,code",
    [
        ({"title": "", "city": "北京"}, "VALIDATION_ERROR"),
        ({"title": "北京", "city": "  "}, "VALIDATION_ERROR"),
        ({"title": "x" * 121, "city": "北京"}, "VALIDATION_ERROR"),
        ({"title": "北京", "city": "x" * 81}, "VALIDATION_ERROR"),
        ({"title": "北京", "city": "北京", "status": "archived"}, "VALIDATION_ERROR"),
        ({"title": "北京", "city": "北京", "startDate": "2026/08/20"}, "VALIDATION_ERROR"),
        ({"title": "北京", "city": "北京", "startDate": "2026-08-21", "endDate": "2026-08-20"}, "INVALID_ROUTE_DATE_RANGE"),
    ],
)
def test_create_route_rejects_invalid_values(app, route_service_db, data, code):
    with app.app_context():
        add_user(1)
        assert_error(lambda service: service.create_route(1, data), code)


def test_create_route_saves_strict_iso_dates(app, route_service_db):
    with app.app_context():
        add_user(1)
        route = create_route(startDate="2026-08-20", endDate="2026-08-22")

        assert route.start_date == date(2026, 8, 20)
        assert route.end_date == date(2026, 8, 22)


def test_list_routes_is_owner_scoped_paginated_and_stably_ordered(app, route_service_db):
    with app.app_context():
        add_user(1)
        add_user(2)
        first = create_route(title="第一条")
        second = create_route(title="第二条")
        create_route(2, title="其他用户")
        first.updated_at = second.updated_at = datetime(2026, 8, 1)
        db.session.commit()

        data = route_service().list_routes(1, limit=1, offset=1)
        assert data["total"] == 2
        assert [route.id for route in data["items"]] == [first.id]
        assert [route.id for route in route_service().list_routes(1)["items"]] == [second.id, first.id]


@pytest.mark.parametrize("kwargs", [{"limit": 0}, {"limit": 101}, {"limit": True}, {"offset": -1}, {"offset": False}])
def test_list_routes_rejects_invalid_pagination(app, route_service_db, kwargs):
    with app.app_context():
        add_user(1)
        assert_error(lambda service: service.list_routes(1, **kwargs), "VALIDATION_ERROR")


def test_route_ownership_conceals_other_users_get_update_and_delete(app, route_service_db):
    with app.app_context():
        add_user(1)
        add_user(2)
        other_route = create_route(2)

        for callback in (
            lambda service: service.get_route(1, other_route.id),
            lambda service: service.update_route(1, other_route.id, {"title": "窃取"}),
            lambda service: service.delete_route(1, other_route.id),
        ):
            assert_error(callback, "ROUTE_NOT_FOUND", 404)
        assert db.session.get(Route, other_route.id) is not None


def test_update_route_preserves_omitted_fields_and_clears_optional_dates(app, route_service_db):
    with app.app_context():
        add_user(1)
        route = create_route(startDate="2026-08-20", endDate="2026-08-22", status="ready")

        updated = route_service().update_route(1, route.id, {"title": "新标题"})
        assert (updated.title, updated.city, updated.status) == ("新标题", "北京", "draft")
        cleared = route_service().update_route(1, route.id, {"startDate": None, "endDate": None})
        assert (cleared.start_date, cleared.end_date) == (None, None)


@pytest.mark.parametrize("payload", [{"title": None}, {"city": None}, {"unknown": "x"}, {}])
def test_update_route_rejects_invalid_patch_payloads(app, route_service_db, payload):
    with app.app_context():
        add_user(1)
        route = create_route()
        assert_error(lambda service: service.update_route(1, route.id, payload), "VALIDATION_ERROR")


def test_route_update_validates_date_range_and_existing_day_dates_atomically(app, route_service_db):
    with app.app_context():
        add_user(1)
        route = create_route(startDate="2026-08-20", endDate="2026-08-25")
        day = route_service().create_route_day(1, route.id, {"date": "2026-08-24"})

        assert_error(
            lambda service: service.update_route(1, route.id, {"startDate": "2026-08-26"}),
            "INVALID_ROUTE_DATE_RANGE",
        )
        assert_error(
            lambda service: service.update_route(1, route.id, {"endDate": "2026-08-23"}),
            "ROUTE_DAY_DATE_OUT_OF_RANGE",
        )
        saved = db.session.get(Route, route.id)
        assert (saved.start_date, saved.end_date, db.session.get(RouteDay, day.id).date) == (
            date(2026, 8, 20), date(2026, 8, 25), date(2026, 8, 24)
        )


def test_route_city_change_is_protected_by_existing_stops(app, route_service_db):
    with app.app_context():
        add_user(1)
        add_attraction(1, city="北京")
        add_attraction(2, city="广州")
        route = create_route()
        day = route_service().create_route_day(1, route.id, {})
        route_service().create_route_stop(1, route.id, day.id, {"attractionId": 1})

        assert_error(lambda service: service.update_route(1, route.id, {"city": "广州"}), "ROUTE_CITY_CONFLICT")
        assert route_service().update_route(1, route.id, {"city": "北京"}).city == "北京"
        route_without_stops = create_route(title="可改城市路线")
        assert route_service().update_route(1, route_without_stops.id, {"city": "广州"}).city == "广州"
        assert db.session.get(Attraction, 2).city == "广州"


def test_explicit_ready_patch_wins_over_ready_route_structure_edit(app, route_service_db):
    with app.app_context():
        add_user(1)
        route = create_route(status="ready")

        assert route_service().update_route(1, route.id, {"title": "编辑后草稿"}).status == "draft"
        route.status = "ready"
        db.session.commit()
        assert route_service().update_route(1, route.id, {"title": "编辑后就绪", "status": "ready"}).status == "ready"
        assert route_service().update_route(1, route.id, {"status": "draft"}).status == "draft"


def test_create_and_update_route_day_assigns_numbers_validates_dates_and_resets_ready(app, route_service_db):
    with app.app_context():
        add_user(1)
        route = create_route(startDate="2026-08-20", endDate="2026-08-22", status="ready")
        first = route_service().create_route_day(1, route.id, {"date": "2026-08-20", "title": "第一天"})
        second = route_service().create_route_day(1, route.id, {"date": "2026-08-21"})

        assert (first.day_number, second.day_number, db.session.get(Route, route.id).status) == (1, 2, "draft")
        updated = route_service().update_route_day(1, route.id, first.id, {"date": None, "title": None})
        assert (updated.date, updated.title) == (None, None)
        assert_error(lambda service: service.create_route_day(1, route.id, {"dayNumber": 9}), "VALIDATION_ERROR")
        assert_error(lambda service: service.create_route_day(1, route.id, {"date": "2026-08-23"}), "ROUTE_DAY_DATE_OUT_OF_RANGE")


def test_route_without_full_date_range_accepts_day_date(app, route_service_db):
    with app.app_context():
        add_user(1)
        route = create_route(startDate="2026-08-20")
        assert route_service().create_route_day(1, route.id, {"date": "2026-09-01"}).date == date(2026, 9, 1)


def test_day_ownership_is_checked_against_visible_parent_route(app, route_service_db):
    with app.app_context():
        add_user(1)
        first_route = create_route()
        second_route = create_route(title="另一条路线")
        other_day = route_service().create_route_day(1, second_route.id, {})

        assert_error(lambda service: service.update_route_day(1, first_route.id, other_day.id, {"title": "错父级"}), "ROUTE_DAY_NOT_FOUND", 404)
        assert_error(lambda service: service.delete_route_day(1, first_route.id, other_day.id), "ROUTE_DAY_NOT_FOUND", 404)


def test_delete_middle_day_cascades_stops_resequences_and_resets_ready(app, route_service_db):
    with app.app_context():
        add_user(1)
        add_attraction(1)
        route = create_route(status="ready")
        first = route_service().create_route_day(1, route.id, {})
        middle = route_service().create_route_day(1, route.id, {})
        last = route_service().create_route_day(1, route.id, {})
        stop = route_service().create_route_stop(1, route.id, middle.id, {"attractionId": 1})
        stop_id = stop.id
        route.status = "ready"
        db.session.commit()

        route_service().delete_route_day(1, route.id, middle.id)
        days = RouteDay.query.filter_by(route_id=route.id).order_by(RouteDay.day_number).all()
        assert [(day.id, day.day_number) for day in days] == [(first.id, 1), (last.id, 2)]
        assert db.session.get(RouteStop, stop_id) is None
        assert db.session.get(Route, route.id).status == "draft"


def test_create_stop_assigns_order_and_validates_active_city_matched_attraction(app, route_service_db):
    with app.app_context():
        add_user(1)
        add_attraction(1, city="北京")
        add_attraction(2, city="北京", is_active=False)
        add_attraction(3, city="广州")
        route = create_route()
        day = route_service().create_route_day(1, route.id, {})
        first = route_service().create_route_stop(1, route.id, day.id, {"attractionId": 1, "note": "观察"})
        second = route_service().create_route_stop(1, route.id, day.id, {"attractionId": 1})

        assert (first.sort_order, second.sort_order, first.note) == (1, 2, "观察")
        assert_error(lambda service: service.create_route_stop(1, route.id, day.id, {"attractionId": 2}), "ATTRACTION_NOT_FOUND", 404)
        assert_error(lambda service: service.create_route_stop(1, route.id, day.id, {"attractionId": 999}), "ATTRACTION_NOT_FOUND", 404)
        assert_error(lambda service: service.create_route_stop(1, route.id, day.id, {"attractionId": 3}), "ATTRACTION_CITY_MISMATCH")


def test_stop_update_rejects_structure_changes_and_resets_ready(app, route_service_db):
    with app.app_context():
        add_user(1)
        add_attraction(1)
        route = create_route(status="ready")
        day = route_service().create_route_day(1, route.id, {})
        stop = route_service().create_route_stop(1, route.id, day.id, {"attractionId": 1})
        route.status = "ready"
        db.session.commit()

        assert route_service().update_route_stop(1, route.id, day.id, stop.id, {"note": "新发现"}).note == "新发现"
        assert db.session.get(Route, route.id).status == "draft"
        for field, value in (("attractionId", 1), ("sortOrder", 2), ("routeDayId", day.id)):
            assert_error(lambda service, field=field, value=value: service.update_route_stop(1, route.id, day.id, stop.id, {field: value}), "VALIDATION_ERROR")


def test_stop_ownership_and_delete_resequence_preserve_attraction(app, route_service_db):
    with app.app_context():
        add_user(1)
        attraction = add_attraction(1)
        route = create_route()
        first_day = route_service().create_route_day(1, route.id, {})
        other_day = route_service().create_route_day(1, route.id, {})
        first = route_service().create_route_stop(1, route.id, first_day.id, {"attractionId": 1})
        middle = route_service().create_route_stop(1, route.id, first_day.id, {"attractionId": 1})
        last = route_service().create_route_stop(1, route.id, first_day.id, {"attractionId": 1})

        assert_error(lambda service: service.update_route_stop(1, route.id, other_day.id, first.id, {"note": "错父级"}), "ROUTE_STOP_NOT_FOUND", 404)
        route_service().delete_route_stop(1, route.id, first_day.id, middle.id)
        stops = RouteStop.query.filter_by(route_day_id=first_day.id).order_by(RouteStop.sort_order).all()
        assert [(stop.id, stop.sort_order) for stop in stops] == [(first.id, 1), (last.id, 2)]
        assert db.session.get(Attraction, attraction.id) is not None


def test_delete_route_removes_owned_aggregate_and_database_errors_roll_back(app, route_service_db, monkeypatch):
    with app.app_context():
        add_user(1)
        route = create_route()
        original_city = route.city
        monkeypatch.setattr(db.session, "commit", lambda: (_ for _ in ()).throw(SQLAlchemyError("boom")))
        assert_error(lambda service: service.update_route(1, route.id, {"city": "广州"}), "DATABASE_ERROR", 500)
        assert db.session.get(Route, route.id).city == original_city
        monkeypatch.undo()
        route_service().delete_route(1, route.id)
        assert db.session.get(Route, route.id) is None


def test_reorder_route_days_is_exact_collision_safe_and_resets_ready(app, route_service_db):
    with app.app_context():
        add_user(1)
        route = create_route(status="ready")
        first = route_service().create_route_day(1, route.id, {})
        second = route_service().create_route_day(1, route.id, {})
        route.status = "ready"
        db.session.commit()

        updated = route_service().reorder_route_days(1, route.id, [second.id, first.id])
        days = RouteDay.query.filter_by(route_id=route.id).order_by(RouteDay.day_number, RouteDay.id).all()

        assert updated.id == route.id
        assert [(day.id, day.day_number) for day in days] == [(second.id, 1), (first.id, 2)]
        assert db.session.get(Route, route.id).status == "draft"


@pytest.mark.parametrize("day_ids", ([1], [1, 1], "1", None, {}, [True]))
def test_reorder_route_days_rejects_non_exact_or_invalid_ids(app, route_service_db, day_ids):
    with app.app_context():
        add_user(1)
        route = create_route()
        first = route_service().create_route_day(1, route.id, {})
        second = route_service().create_route_day(1, route.id, {})
        payload = [first.id] if day_ids == [1] else day_ids

        assert_error(lambda service: service.reorder_route_days(1, route.id, payload), "INVALID_ROUTE_DAY_ORDER")
        assert [(day.id, day.day_number) for day in RouteDay.query.filter_by(route_id=route.id).order_by(RouteDay.day_number).all()] == [(first.id, 1), (second.id, 2)]


def test_reorder_route_days_rejects_foreign_day_hides_other_user_and_accepts_empty_route(app, route_service_db):
    with app.app_context():
        add_user(1)
        add_user(2)
        route = create_route()
        foreign_route = create_route(2)
        foreign_day = route_service().create_route_day(2, foreign_route.id, {})

        assert_error(lambda service: service.reorder_route_days(1, route.id, [foreign_day.id]), "INVALID_ROUTE_DAY_ORDER")
        assert_error(lambda service: service.reorder_route_days(1, foreign_route.id, []), "ROUTE_NOT_FOUND", 404)
        assert route_service().reorder_route_days(1, route.id, []).id == route.id


def test_reorder_route_stops_is_exact_collision_safe_and_resets_ready(app, route_service_db):
    with app.app_context():
        add_user(1)
        add_attraction(1)
        route = create_route(status="ready")
        day = route_service().create_route_day(1, route.id, {})
        first = route_service().create_route_stop(1, route.id, day.id, {"attractionId": 1})
        second = route_service().create_route_stop(1, route.id, day.id, {"attractionId": 1})
        route.status = "ready"
        db.session.commit()

        updated = route_service().reorder_route_stops(1, route.id, day.id, [second.id, first.id])
        stops = RouteStop.query.filter_by(route_day_id=day.id).order_by(RouteStop.sort_order, RouteStop.id).all()

        assert updated.id == route.id
        assert [(stop.id, stop.sort_order) for stop in stops] == [(second.id, 1), (first.id, 2)]
        assert db.session.get(Route, route.id).status == "draft"


@pytest.mark.parametrize("stop_ids", ([1], [1, 1], "1", None, {}, [True]))
def test_reorder_route_stops_rejects_non_exact_or_invalid_ids(app, route_service_db, stop_ids):
    with app.app_context():
        add_user(1)
        add_attraction(1)
        route = create_route()
        day = route_service().create_route_day(1, route.id, {})
        first = route_service().create_route_stop(1, route.id, day.id, {"attractionId": 1})
        second = route_service().create_route_stop(1, route.id, day.id, {"attractionId": 1})
        payload = [first.id] if stop_ids == [1] else stop_ids

        assert_error(lambda service: service.reorder_route_stops(1, route.id, day.id, payload), "INVALID_ROUTE_STOP_ORDER")
        assert [(stop.id, stop.sort_order) for stop in RouteStop.query.filter_by(route_day_id=day.id).order_by(RouteStop.sort_order).all()] == [(first.id, 1), (second.id, 2)]


def test_reorder_route_stops_rejects_foreign_stop_wrong_parent_and_accepts_empty_day(app, route_service_db):
    with app.app_context():
        add_user(1)
        add_attraction(1)
        route = create_route()
        first_day = route_service().create_route_day(1, route.id, {})
        empty_day = route_service().create_route_day(1, route.id, {})
        foreign_stop = route_service().create_route_stop(1, route.id, first_day.id, {"attractionId": 1})

        assert_error(lambda service: service.reorder_route_stops(1, route.id, empty_day.id, [foreign_stop.id]), "INVALID_ROUTE_STOP_ORDER")
        assert_error(lambda service: service.reorder_route_stops(1, route.id, 999, []), "ROUTE_DAY_NOT_FOUND", 404)
        assert route_service().reorder_route_stops(1, route.id, empty_day.id, []).id == route.id
