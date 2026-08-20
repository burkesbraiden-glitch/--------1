import pytest
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Attraction, Child, ExplorationPlan, Route, RouteDay, RouteStop, User
from app.services.routes import RouteError, delete_route, delete_route_day, delete_route_stop


@pytest.fixture()
def delete_guard_db(app):
    with app.app_context():
        def enable_foreign_keys(dbapi_connection, _connection_record):
            if dbapi_connection.__class__.__module__.startswith("sqlite3"):
                dbapi_connection.execute("PRAGMA foreign_keys=ON")

        event.listen(db.engine, "connect", enable_foreign_keys)
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()
        event.remove(db.engine, "connect", enable_foreign_keys)


def seed_route_tree():
    owner = User(id=1, phone="13800138000", nickname="路线家长")
    other_user = User(id=2, phone="13900139000", nickname="其他家长")
    child = Child(id=10, user_id=1, name="孩子甲", age=8, age_group="7-12", interests=[])
    attraction = Attraction(id=100, name="故宫博物院", city="北京", summary="观察屋檐。", tags=[])
    route = Route(id=1, user_id=1, title="北京探索", city="北京", status="ready")
    first_day = RouteDay(id=1000, route_id=1, day_number=1, title="第一天")
    second_day = RouteDay(id=1001, route_id=1, day_number=2, title="第二天")
    first_stop = RouteStop(id=10000, route_day_id=1000, attraction_id=100, sort_order=1)
    second_stop = RouteStop(id=10001, route_day_id=1000, attraction_id=100, sort_order=2)
    third_stop = RouteStop(id=10002, route_day_id=1001, attraction_id=100, sort_order=1)
    other_route = Route(id=2, user_id=2, title="广州探索", city="广州", status="ready")
    other_day = RouteDay(id=2000, route_id=2, day_number=1)
    other_stop = RouteStop(id=20000, route_day_id=2000, attraction_id=100, sort_order=1)
    db.session.add_all([
        owner,
        other_user,
        child,
        attraction,
        route,
        first_day,
        second_day,
        first_stop,
        second_stop,
        third_stop,
        other_route,
        other_day,
        other_stop,
    ])
    db.session.commit()
    return {
        "owner": owner,
        "child": child,
        "route": route,
        "first_day": first_day,
        "second_day": second_day,
        "first_stop": first_stop,
        "second_stop": second_stop,
        "third_stop": third_stop,
        "other_route": other_route,
        "other_day": other_day,
        "other_stop": other_stop,
    }


def add_linked_plan(data, *, status="ready"):
    plan = ExplorationPlan(
        id=9000,
        user_id=data["owner"].id,
        child_id=data["child"].id,
        route_stop_id=data["first_stop"].id,
        title="故宫亲子探索",
        destination="故宫博物院",
        age_group="7-12",
        duration="60分钟",
        interests=[],
        status=status,
        source_snapshot={"schemaVersion": 1},
    )
    db.session.add(plan)
    db.session.commit()
    return plan


def add_manual_plan(data):
    plan = ExplorationPlan(
        id=9001,
        user_id=data["owner"].id,
        child_id=data["child"].id,
        title="手动计划",
        destination="首都博物馆",
        age_group="7-12",
        duration="半天",
        interests=[],
        status="ready",
    )
    db.session.add(plan)
    db.session.commit()
    return plan


def assert_guard(callback, code):
    try:
        callback()
    except RouteError as error:
        assert error.code == code
        assert error.status_code == 409
    except SQLAlchemyError as error:
        db.session.rollback()
        pytest.fail(f"expected {code} business guard, received database error: {error}")
    else:
        pytest.fail(f"expected {code} business guard")


def assert_route_error(callback, code):
    with pytest.raises(RouteError) as error:
        callback()
    assert error.value.code == code
    assert error.value.status_code == 404


def test_stop_delete_guard_preserves_plan_link_order_and_route_state(app, delete_guard_db):
    with app.app_context():
        data = seed_route_tree()
        plan = add_linked_plan(data)

        assert_guard(
            lambda: delete_route_stop(1, data["route"].id, data["first_day"].id, data["first_stop"].id),
            "ROUTE_STOP_HAS_EXPLORATION_PLANS",
        )

        assert db.session.get(RouteStop, data["first_stop"].id) is not None
        assert db.session.get(ExplorationPlan, plan.id).route_stop_id == data["first_stop"].id
        assert [(stop.id, stop.sort_order) for stop in RouteStop.query.filter_by(route_day_id=data["first_day"].id).order_by(RouteStop.sort_order).all()] == [
            (data["first_stop"].id, 1),
            (data["second_stop"].id, 2),
        ]
        assert db.session.get(Route, data["route"].id).status == "ready"


def test_day_delete_guard_preserves_entire_day_chain_and_number(app, delete_guard_db):
    with app.app_context():
        data = seed_route_tree()
        plan = add_linked_plan(data)

        assert_guard(
            lambda: delete_route_day(1, data["route"].id, data["first_day"].id),
            "ROUTE_DAY_HAS_EXPLORATION_PLANS",
        )

        assert db.session.get(RouteDay, data["first_day"].id).day_number == 1
        assert {stop.id for stop in RouteStop.query.filter_by(route_day_id=data["first_day"].id)} == {
            data["first_stop"].id,
            data["second_stop"].id,
        }
        assert db.session.get(ExplorationPlan, plan.id).route_stop_id == data["first_stop"].id
        assert db.session.get(Route, data["route"].id).status == "ready"


def test_route_delete_guard_preserves_descendant_chain_and_plan(app, delete_guard_db):
    with app.app_context():
        data = seed_route_tree()
        plan = add_linked_plan(data)

        assert_guard(
            lambda: delete_route(1, data["route"].id),
            "ROUTE_HAS_EXPLORATION_PLANS",
        )

        assert db.session.get(Route, data["route"].id) is not None
        assert db.session.get(RouteDay, data["first_day"].id) is not None
        assert db.session.get(RouteStop, data["first_stop"].id) is not None
        assert db.session.get(ExplorationPlan, plan.id).route_stop_id == data["first_stop"].id


@pytest.mark.parametrize("status", ["draft", "ready", "in-progress", "completed"])
def test_linked_plan_status_does_not_change_stop_guard(app, delete_guard_db, status):
    with app.app_context():
        data = seed_route_tree()
        add_linked_plan(data, status=status)

        assert_guard(
            lambda: delete_route_stop(1, data["route"].id, data["first_day"].id, data["first_stop"].id),
            "ROUTE_STOP_HAS_EXPLORATION_PLANS",
        )


def test_unlinked_delete_paths_keep_existing_resequence_and_draft_behavior(app, delete_guard_db):
    with app.app_context():
        data = seed_route_tree()

        delete_route_stop(1, data["route"].id, data["first_day"].id, data["first_stop"].id)
        assert [(stop.id, stop.sort_order) for stop in RouteStop.query.filter_by(route_day_id=data["first_day"].id).order_by(RouteStop.sort_order).all()] == [
            (data["second_stop"].id, 1)
        ]
        assert db.session.get(Route, data["route"].id).status == "draft"

        delete_route_day(1, data["route"].id, data["first_day"].id)
        assert [(day.id, day.day_number) for day in RouteDay.query.filter_by(route_id=data["route"].id).order_by(RouteDay.day_number).all()] == [
            (data["second_day"].id, 1)
        ]
        delete_route(1, data["route"].id)
        assert db.session.get(Route, data["route"].id) is None


@pytest.mark.parametrize("target", ["stop", "day", "route"])
def test_manual_null_source_plan_does_not_block_deletes(app, delete_guard_db, target):
    with app.app_context():
        data = seed_route_tree()
        manual_plan = add_manual_plan(data)

        if target == "stop":
            delete_route_stop(1, data["route"].id, data["first_day"].id, data["first_stop"].id)
            assert db.session.get(RouteStop, data["first_stop"].id) is None
        elif target == "day":
            delete_route_day(1, data["route"].id, data["first_day"].id)
            assert db.session.get(RouteDay, data["first_day"].id) is None
        else:
            delete_route(1, data["route"].id)
            assert db.session.get(Route, data["route"].id) is None
        assert db.session.get(ExplorationPlan, manual_plan.id).route_stop_id is None


def test_delete_guards_preserve_other_user_ownership_concealment(app, delete_guard_db):
    with app.app_context():
        data = seed_route_tree()

        assert_route_error(lambda: delete_route(1, data["other_route"].id), "ROUTE_NOT_FOUND")
        assert_route_error(lambda: delete_route_day(1, data["other_route"].id, data["other_day"].id), "ROUTE_NOT_FOUND")
        assert_route_error(
            lambda: delete_route_stop(1, data["other_route"].id, data["other_day"].id, data["other_stop"].id),
            "ROUTE_NOT_FOUND",
        )
