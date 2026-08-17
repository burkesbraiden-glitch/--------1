from datetime import date

import pytest
from sqlalchemy import CheckConstraint, Date, UniqueConstraint, event
from sqlalchemy.exc import IntegrityError

from app import models
from app.extensions import db


def _route_models():
    assert hasattr(models, "Route")
    assert hasattr(models, "RouteDay")
    assert hasattr(models, "RouteStop")
    return models.Route, models.RouteDay, models.RouteStop


def _check_sql(table):
    return {
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }


def _unique_columns(table):
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


@pytest.fixture()
def route_db(app):
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


def _make_user(user_id=1):
    return models.User(id=user_id, phone=f"1380000{user_id:04d}", nickname="路线家长")


def _make_attraction(attraction_id=1):
    return models.Attraction(
        id=attraction_id,
        name="故宫博物院",
        city="北京",
        summary="观察古建筑。",
        tags=["历史"],
    )


def _make_route(route_id=1, user_id=1):
    Route, _, _ = _route_models()
    return Route(
        id=route_id,
        user_id=user_id,
        title="北京探索路线",
        city="北京",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 3),
    )


def test_route_schema_relationships_and_status_constraint():
    Route, RouteDay, _ = _route_models()
    table = Route.__table__

    assert set(table.c.keys()) == {
        "id", "user_id", "title", "city", "start_date", "end_date", "status", "created_at", "updated_at"
    }
    assert table.c.user_id.nullable is False
    assert table.c.user_id.index is True
    assert table.c.title.type.length == 120
    assert table.c.city.type.length == 80
    assert isinstance(table.c.start_date.type, Date)
    assert isinstance(table.c.end_date.type, Date)
    assert table.c.status.default.arg == "draft"
    assert table.c.status.server_default is not None
    assert "status IN ('draft', 'ready')" in _check_sql(table)
    assert list(table.c.user_id.foreign_keys)[0].target_fullname == "users.id"
    assert list(table.c.user_id.foreign_keys)[0].ondelete == "CASCADE"
    assert Route.user.property.back_populates == "routes"
    assert Route.days.property.mapper.class_ is RouteDay
    assert Route.days.property.back_populates == "route"
    assert "delete-orphan" in Route.days.property.cascade
    assert Route.days.property.passive_deletes is True
    assert models.User.routes.property.mapper.class_ is Route
    assert models.User.routes.property.back_populates == "user"
    assert "delete-orphan" in models.User.routes.property.cascade
    assert models.User.routes.property.passive_deletes is True


def test_route_day_schema_relationships_and_constraints():
    Route, RouteDay, RouteStop = _route_models()
    table = RouteDay.__table__

    assert set(table.c.keys()) == {"id", "route_id", "day_number", "date", "title", "created_at", "updated_at"}
    assert table.c.route_id.nullable is False
    assert table.c.route_id.index is True
    assert isinstance(table.c.date.type, Date)
    assert table.c.title.type.length == 120
    assert ("route_id", "day_number") in _unique_columns(table)
    assert "day_number > 0" in _check_sql(table)
    assert list(table.c.route_id.foreign_keys)[0].target_fullname == "routes.id"
    assert list(table.c.route_id.foreign_keys)[0].ondelete == "CASCADE"
    assert RouteDay.route.property.mapper.class_ is Route
    assert RouteDay.route.property.back_populates == "days"
    assert RouteDay.stops.property.mapper.class_ is RouteStop
    assert RouteDay.stops.property.back_populates == "route_day"
    assert "delete-orphan" in RouteDay.stops.property.cascade
    assert RouteDay.stops.property.passive_deletes is True


def test_route_stop_schema_relationships_and_constraints():
    _, RouteDay, RouteStop = _route_models()
    table = RouteStop.__table__

    assert set(table.c.keys()) == {"id", "route_day_id", "attraction_id", "sort_order", "note", "created_at", "updated_at"}
    assert table.c.route_day_id.nullable is False
    assert table.c.route_day_id.index is True
    assert table.c.attraction_id.nullable is False
    assert table.c.attraction_id.index is True
    assert ("route_day_id", "sort_order") in _unique_columns(table)
    assert "sort_order > 0" in _check_sql(table)
    assert list(table.c.route_day_id.foreign_keys)[0].target_fullname == "route_days.id"
    assert list(table.c.route_day_id.foreign_keys)[0].ondelete == "CASCADE"
    assert list(table.c.attraction_id.foreign_keys)[0].target_fullname == "attractions.id"
    assert list(table.c.attraction_id.foreign_keys)[0].ondelete == "RESTRICT"
    assert RouteStop.route_day.property.mapper.class_ is RouteDay
    assert RouteStop.route_day.property.back_populates == "stops"
    assert RouteStop.attraction.property.mapper.class_ is models.Attraction
    assert not hasattr(models.Attraction, "route_stops")


def test_route_defaults_dates_and_relationships_persist(app, route_db):
    Route, RouteDay, RouteStop = _route_models()
    with app.app_context():
        db.session.add_all([_make_user(), _make_attraction()])
        db.session.commit()
        route = _make_route()
        day = RouteDay(id=10, route=route, day_number=1, date=date(2026, 10, 1), title="第一天")
        stop = RouteStop(id=100, route_day=day, attraction_id=1, sort_order=1, note="看屋檐")
        db.session.add(stop)
        db.session.commit()

        saved_route = db.session.get(Route, 1)
        assert saved_route.status == "draft"
        assert saved_route.start_date == date(2026, 10, 1)
        assert saved_route.end_date == date(2026, 10, 3)
        assert db.session.get(models.User, 1).routes[0].id == saved_route.id
        assert saved_route.days[0].id == day.id
        assert saved_route.days[0].stops[0].attraction.id == 1


def test_route_status_and_day_number_constraints_are_enforced(app, route_db):
    _, RouteDay, _ = _route_models()
    with app.app_context():
        db.session.add(_make_user())
        db.session.commit()
        db.session.add(_make_route())
        db.session.commit()

        db.session.add(_make_route(2, 1).__class__(id=2, user_id=1, title="无效", city="北京", status="archived"))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        db.session.add(RouteDay(id=10, route_id=1, day_number=0))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_route_day_and_stop_unique_and_positive_constraints_are_enforced(app, route_db):
    _, RouteDay, RouteStop = _route_models()
    with app.app_context():
        db.session.add_all([_make_user(), _make_attraction(), _make_route()])
        db.session.commit()
        db.session.add(RouteDay(id=10, route_id=1, day_number=1))
        db.session.commit()

        db.session.add(RouteDay(id=11, route_id=1, day_number=1))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        db.session.add(RouteStop(id=100, route_day_id=10, attraction_id=1, sort_order=0))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        db.session.add(RouteStop(id=100, route_day_id=10, attraction_id=1, sort_order=1))
        db.session.commit()
        db.session.add(RouteStop(id=101, route_day_id=10, attraction_id=1, sort_order=1))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_deleting_route_cascades_days_and_stops(app, route_db):
    Route, RouteDay, RouteStop = _route_models()
    with app.app_context():
        db.session.add_all([_make_user(), _make_attraction(), _make_route()])
        db.session.commit()
        db.session.add_all([
            RouteDay(id=10, route_id=1, day_number=1),
            RouteStop(id=100, route_day_id=10, attraction_id=1, sort_order=1),
        ])
        db.session.commit()

        db.session.delete(db.session.get(Route, 1))
        db.session.commit()

        assert RouteDay.query.count() == 0
        assert RouteStop.query.count() == 0


def test_deleting_route_day_cascades_stops_and_stop_delete_preserves_attraction(app, route_db):
    _, RouteDay, RouteStop = _route_models()
    with app.app_context():
        db.session.add_all([_make_user(), _make_attraction(), _make_route()])
        db.session.commit()
        db.session.add_all([
            RouteDay(id=10, route_id=1, day_number=1),
            RouteStop(id=100, route_day_id=10, attraction_id=1, sort_order=1),
        ])
        db.session.commit()

        db.session.delete(db.session.get(RouteDay, 10))
        db.session.commit()
        assert RouteStop.query.count() == 0
        assert db.session.get(models.Attraction, 1) is not None
