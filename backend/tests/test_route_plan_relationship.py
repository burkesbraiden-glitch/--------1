import importlib.util
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import JSON, UniqueConstraint, event

from app.extensions import db
from app.models import Attraction, Child, ExplorationPlan, Route, RouteDay, RouteStop, User


def _load_route_plan_migration():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "ea8f05d3f3af_link_exploration_plans_to_route_stops.py"
    )
    spec = importlib.util.spec_from_file_location(
        "route_plan_migration_for_test", migration_path
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_migration_downgrade_drops_fk_before_composite_unique(monkeypatch):
    migration = _load_route_plan_migration()
    calls = []

    monkeypatch.setattr(migration.op, "f", lambda constraint_name: constraint_name)
    monkeypatch.setattr(
        migration.op,
        "drop_constraint",
        lambda constraint_name, table_name, type_: calls.append(
            ("constraint", constraint_name, table_name, type_)
        ),
    )
    monkeypatch.setattr(
        migration.op,
        "drop_column",
        lambda table_name, column_name: calls.append(
            ("column", table_name, column_name)
        ),
    )

    migration.downgrade()

    assert calls == [
        (
            "constraint",
            "fk_exploration_plans_route_stop_id_route_stops",
            "exploration_plans",
            "foreignkey",
        ),
        (
            "constraint",
            "route_stop_child_unique",
            "exploration_plans",
            "unique",
        ),
        ("column", "exploration_plans", "source_snapshot"),
        ("column", "exploration_plans", "route_stop_id"),
    ]


def _unique_columns(table):
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


@pytest.fixture()
def relationship_db(app):
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


def _make_plan(plan_id, child_id, route_stop_id=None):
    return ExplorationPlan(
        id=plan_id,
        user_id=1,
        child_id=child_id,
        route_stop_id=route_stop_id,
        title=f"探索计划{plan_id}",
        destination="故宫博物院",
        age_group="7-12",
        duration="3小时",
        interests=["古建筑"],
        status="ready",
    )


def test_route_stop_source_columns_foreign_key_and_unique_contract():
    table = ExplorationPlan.__table__

    assert table.c.route_stop_id.nullable is True
    assert table.c.source_snapshot.nullable is True
    assert isinstance(table.c.source_snapshot.type, JSON)

    route_stop_foreign_keys = list(table.c.route_stop_id.foreign_keys)
    assert len(route_stop_foreign_keys) == 1
    assert route_stop_foreign_keys[0].target_fullname == "route_stops.id"
    assert route_stop_foreign_keys[0].ondelete == "RESTRICT"

    unique_columns = _unique_columns(table)
    assert ("route_stop_id", "child_id") in unique_columns
    assert ("route_stop_id",) not in unique_columns


def test_route_stop_and_plan_relationships_protect_the_source_link():
    assert ExplorationPlan.route_stop.property.mapper.class_ is RouteStop
    assert ExplorationPlan.route_stop.property.back_populates == "exploration_plans"
    assert RouteStop.exploration_plans.property.mapper.class_ is ExplorationPlan
    assert RouteStop.exploration_plans.property.back_populates == "route_stop"
    assert RouteStop.exploration_plans.property.passive_deletes == "all"
    assert "delete" not in RouteStop.exploration_plans.property.cascade
    assert "delete-orphan" not in RouteStop.exploration_plans.property.cascade


def test_manual_plans_keep_nullable_route_source_and_snapshot(app, relationship_db):
    with app.app_context():
        db.session.add_all([
            User(id=1, phone="13800138000", nickname="路线家长"),
            Child(id=10, user_id=1, name="孩子甲", age=8, age_group="7-12", interests=[], is_default=True),
        ])
        db.session.commit()

        first = _make_plan(100, 10)
        second = _make_plan(101, 10)
        db.session.add_all([first, second])
        db.session.commit()

        assert first.route_stop_id is None
        assert first.source_snapshot is None
        assert second.route_stop_id is None
        assert ExplorationPlan.query.count() == 2


def test_same_stop_supports_one_generated_plan_per_child(app, relationship_db):
    with app.app_context():
        db.session.add_all([
            User(id=1, phone="13800138000", nickname="路线家长"),
            Child(id=10, user_id=1, name="孩子甲", age=8, age_group="7-12", interests=[], is_default=True),
            Child(id=11, user_id=1, name="孩子乙", age=10, age_group="7-12", interests=[], is_default=False),
            Attraction(id=1, name="故宫博物院", city="北京", summary="观察古建筑。", tags=[]),
            Route(id=1, user_id=1, title="北京路线", city="北京", start_date=date(2026, 10, 1), end_date=date(2026, 10, 1)),
            RouteDay(id=10, route_id=1, day_number=1),
            RouteStop(id=100, route_day_id=10, attraction_id=1, sort_order=1),
        ])
        db.session.commit()

        db.session.add_all([_make_plan(1000, 10, 100), _make_plan(1001, 11, 100)])
        db.session.commit()

        stop = db.session.get(RouteStop, 100)
        assert {plan.child_id for plan in stop.exploration_plans} == {10, 11}
