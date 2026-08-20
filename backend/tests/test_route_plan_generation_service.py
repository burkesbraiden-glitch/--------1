import json
from datetime import date

import pytest
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import (
    Attraction,
    Child,
    ExplorationPlan,
    GuideCard,
    JourneyRecord,
    Route,
    RouteDay,
    RouteStop,
    Task,
    User,
)
from app.services.route_plan_generation import (
    RoutePlanGenerationError,
    generate_exploration_plans_from_route,
)


@pytest.fixture()
def generation_db(app):
    next_plan_id = 10000

    def enable_foreign_keys(dbapi_connection, _connection_record):
        if dbapi_connection.__class__.__module__.startswith("sqlite3"):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

    def assign_plan_id(_mapper, _connection, target):
        nonlocal next_plan_id
        if target.id is None:
            target.id = next_plan_id
            next_plan_id += 1

    with app.app_context():
        event.listen(db.engine, "connect", enable_foreign_keys)
        event.listen(ExplorationPlan, "before_insert", assign_plan_id)
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()
        event.remove(ExplorationPlan, "before_insert", assign_plan_id)
        event.remove(db.engine, "connect", enable_foreign_keys)


def seed_generation_context(*, route_status="ready"):
    owner = User(id=1, phone="13800138000", nickname="路线家长")
    other_user = User(id=2, phone="13900139000", nickname="其他家长")
    child_a = Child(
        id=10,
        user_id=owner.id,
        name="孩子甲",
        age=8,
        age_group="7-12",
        interests=["古建筑", "绘画"],
        is_default=True,
    )
    child_b = Child(
        id=11,
        user_id=owner.id,
        name="孩子乙",
        age=10,
        age_group="7-12",
        interests=["历史故事"],
        is_default=False,
    )
    other_child = Child(
        id=20,
        user_id=other_user.id,
        name="其他孩子",
        age=9,
        age_group="7-12",
        interests=["科学"],
        is_default=True,
    )
    first_attraction = Attraction(
        id=100,
        name="故宫博物院",
        city="北京",
        district="东城区",
        address="景山前街4号",
        summary="观察屋檐上的小兽。",
        tags=["历史", "古建筑"],
        recommended_duration_minutes=60,
        cover_image="/images/palace.jpg",
    )
    second_attraction = Attraction(
        id=101,
        name="中国国家博物馆",
        city="北京",
        district="东城区",
        address="东长安街16号",
        summary="寻找一件最想了解的文物。",
        tags=["历史", "文物"],
        recommended_duration_minutes=None,
        cover_image=None,
    )
    other_attraction = Attraction(
        id=200,
        name="广州博物馆",
        city="广州",
        summary="其他路线景点。",
        tags=["历史"],
    )
    route = Route(
        id=1,
        user_id=owner.id,
        title="北京文化探索",
        city="北京",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 2),
        status=route_status,
    )
    first_day = RouteDay(
        id=1000,
        route_id=route.id,
        day_number=1,
        date=date(2026, 10, 1),
        title="故宫观察日",
    )
    second_day = RouteDay(
        id=1001,
        route_id=route.id,
        day_number=2,
        date=date(2026, 10, 2),
        title="博物馆发现日",
    )
    first_stop = RouteStop(
        id=10000,
        route_day_id=first_day.id,
        attraction_id=first_attraction.id,
        sort_order=1,
        note="先看屋顶。",
    )
    second_stop = RouteStop(
        id=10001,
        route_day_id=second_day.id,
        attraction_id=second_attraction.id,
        sort_order=1,
        note="挑一件文物。",
    )
    other_route = Route(
        id=2,
        user_id=other_user.id,
        title="广州文化探索",
        city="广州",
        status="ready",
    )
    other_day = RouteDay(id=2000, route_id=other_route.id, day_number=1)
    other_stop = RouteStop(
        id=20000,
        route_day_id=other_day.id,
        attraction_id=other_attraction.id,
        sort_order=1,
    )
    db.session.add_all([
        owner,
        other_user,
        child_a,
        child_b,
        other_child,
        first_attraction,
        second_attraction,
        other_attraction,
        route,
        first_day,
        second_day,
        first_stop,
        second_stop,
        other_route,
        other_day,
        other_stop,
    ])
    db.session.commit()
    return {
        "owner": owner,
        "other_user": other_user,
        "child_a": child_a,
        "child_b": child_b,
        "other_child": other_child,
        "route": route,
        "first_day": first_day,
        "second_day": second_day,
        "first_stop": first_stop,
        "second_stop": second_stop,
        "first_attraction": first_attraction,
        "second_attraction": second_attraction,
        "other_route": other_route,
        "other_stop": other_stop,
    }


def assert_error(callback, code, status_code):
    with pytest.raises(RoutePlanGenerationError) as error:
        callback()
    assert error.value.code == code
    assert error.value.status_code == status_code


def test_generates_ready_plan_with_snapshot_and_no_downstream_artifacts(app, generation_db):
    with app.app_context():
        data = seed_generation_context()

        result = generate_exploration_plans_from_route(
            data["owner"], data["route"].id, data["child_a"].id, [data["first_stop"].id]
        )

        assert result["route"] is data["route"]
        assert result["child"] is data["child_a"]
        assert [(item["routeStopId"], item["result"]) for item in result["results"]] == [
            (data["first_stop"].id, "created")
        ]
        plan = result["results"][0]["plan"]
        assert (plan.user_id, plan.child_id, plan.route_stop_id) == (1, 10, 10000)
        assert (plan.title, plan.destination, plan.age_group, plan.duration, plan.status) == (
            "故宫博物院亲子探索",
            "故宫博物院",
            "7-12",
            "60分钟",
            "ready",
        )
        assert plan.completed_at is None
        assert plan.interests == ["古建筑", "绘画"]
        assert plan.interests is not data["child_a"].interests
        assert plan.source_snapshot["attraction"]["tags"] is not data["first_attraction"].tags
        assert plan.source_snapshot == {
            "schemaVersion": 1,
            "route": {
                "id": 1,
                "title": "北京文化探索",
                "city": "北京",
                "startDate": "2026-10-01",
                "endDate": "2026-10-02",
            },
            "day": {
                "id": 1000,
                "dayNumber": 1,
                "date": "2026-10-01",
                "title": "故宫观察日",
            },
            "stop": {"id": 10000, "sortOrder": 1, "note": "先看屋顶。"},
            "attraction": {
                "id": 100,
                "name": "故宫博物院",
                "city": "北京",
                "district": "东城区",
                "address": "景山前街4号",
                "summary": "观察屋檐上的小兽。",
                "tags": ["历史", "古建筑"],
                "recommendedDurationMinutes": 60,
                "coverImage": "/images/palace.jpg",
            },
        }
        json.dumps(plan.source_snapshot)
        assert Task.query.count() == 0
        assert GuideCard.query.count() == 0
        assert JourneyRecord.query.count() == 0


def test_uses_route_stop_request_order_and_duration_fallback(app, generation_db):
    with app.app_context():
        data = seed_generation_context()

        result = generate_exploration_plans_from_route(
            data["owner"],
            data["route"].id,
            data["child_a"].id,
            [data["second_stop"].id, data["first_stop"].id],
        )

        assert [(item["routeStopId"], item["result"]) for item in result["results"]] == [
            (data["second_stop"].id, "created"),
            (data["first_stop"].id, "created"),
        ]
        assert result["results"][0]["plan"].duration == "按行程安排"
        assert ExplorationPlan.query.count() == 2

        repeated = generate_exploration_plans_from_route(
            data["owner"],
            data["route"].id,
            data["child_a"].id,
            [data["second_stop"].id, data["first_stop"].id],
        )
        assert [item["result"] for item in repeated["results"]] == ["existing", "existing"]
        assert ExplorationPlan.query.count() == 2


def test_conceals_other_users_route_and_rejects_draft_routes(app, generation_db):
    with app.app_context():
        data = seed_generation_context()

        assert_error(
            lambda: generate_exploration_plans_from_route(
                data["owner"], data["other_route"].id, data["child_a"].id, [data["other_stop"].id]
            ),
            "ROUTE_NOT_FOUND",
            404,
        )
        assert ExplorationPlan.query.count() == 0

        data["route"].status = "draft"
        db.session.commit()
        assert_error(
            lambda: generate_exploration_plans_from_route(
                data["owner"], data["route"].id, data["child_a"].id, [data["first_stop"].id]
            ),
            "ROUTE_NOT_READY",
            409,
        )
        assert data["route"].status == "draft"
        assert ExplorationPlan.query.count() == 0


@pytest.mark.parametrize("child_id", [None, True, 0, -1, "10"])
def test_requires_an_explicit_positive_integer_child_id(app, generation_db, child_id):
    with app.app_context():
        data = seed_generation_context()
        assert_error(
            lambda: generate_exploration_plans_from_route(
                data["owner"], data["route"].id, child_id, [data["first_stop"].id]
            ),
            "VALIDATION_ERROR",
            400,
        )
        assert ExplorationPlan.query.count() == 0


def test_rejects_missing_or_foreign_child_without_default_fallback(app, generation_db):
    with app.app_context():
        data = seed_generation_context()

        for child_id in (999, data["other_child"].id):
            assert_error(
                lambda child_id=child_id: generate_exploration_plans_from_route(
                    data["owner"], data["route"].id, child_id, [data["first_stop"].id]
                ),
                "CHILD_NOT_FOUND",
                404,
            )
        assert ExplorationPlan.query.count() == 0


@pytest.mark.parametrize(
    "route_stop_ids",
    [None, (), "10000", [], [True], [0], [-1], ["10000"], [10000, 10000]],
)
def test_validates_route_stop_selection_shape_values_and_duplicates(app, generation_db, route_stop_ids):
    with app.app_context():
        data = seed_generation_context()
        assert_error(
            lambda: generate_exploration_plans_from_route(
                data["owner"], data["route"].id, data["child_a"].id, route_stop_ids
            ),
            "VALIDATION_ERROR",
            400,
        )
        assert ExplorationPlan.query.count() == 0


def test_rejects_non_descendant_stop_and_keeps_entire_batch_empty(app, generation_db):
    with app.app_context():
        data = seed_generation_context()

        for route_stop_ids in ([99999], [data["first_stop"].id, data["other_stop"].id]):
            assert_error(
                lambda route_stop_ids=route_stop_ids: generate_exploration_plans_from_route(
                    data["owner"], data["route"].id, data["child_a"].id, route_stop_ids
                ),
                "ROUTE_STOP_NOT_FOUND",
                404,
            )
            assert ExplorationPlan.query.count() == 0


def test_is_idempotent_per_stop_and_child_and_supports_mixed_batches(app, generation_db):
    with app.app_context():
        data = seed_generation_context()
        first = generate_exploration_plans_from_route(
            data["owner"], data["route"].id, data["child_a"].id, [data["first_stop"].id]
        )
        generated_plan = first["results"][0]["plan"]
        generated_snapshot = json.loads(json.dumps(generated_plan.source_snapshot))
        generated_fields = (
            generated_plan.title,
            generated_plan.destination,
            generated_plan.duration,
            list(generated_plan.interests),
        )

        data["route"].title = "后续路线标题"
        data["first_day"].title = "后续日标题"
        data["first_stop"].note = "后续 Stop 备注"
        data["first_attraction"].name = "后续景点名称"
        data["first_attraction"].summary = "后续景点简介"
        data["child_a"].interests = ["后续兴趣"]
        db.session.commit()

        second = generate_exploration_plans_from_route(
            data["owner"],
            data["route"].id,
            data["child_a"].id,
            [data["first_stop"].id, data["second_stop"].id],
        )

        assert [(item["routeStopId"], item["result"]) for item in second["results"]] == [
            (data["first_stop"].id, "existing"),
            (data["second_stop"].id, "created"),
        ]
        existing_plan = second["results"][0]["plan"]
        assert existing_plan.id == generated_plan.id
        assert existing_plan.source_snapshot == generated_snapshot
        assert (
            existing_plan.title,
            existing_plan.destination,
            existing_plan.duration,
            existing_plan.interests,
        ) == generated_fields
        assert ExplorationPlan.query.count() == 2


def test_allows_the_same_stop_for_different_children(app, generation_db):
    with app.app_context():
        data = seed_generation_context()

        first = generate_exploration_plans_from_route(
            data["owner"], data["route"].id, data["child_a"].id, [data["first_stop"].id]
        )
        second = generate_exploration_plans_from_route(
            data["owner"], data["route"].id, data["child_b"].id, [data["first_stop"].id]
        )

        assert first["results"][0]["result"] == second["results"][0]["result"] == "created"
        assert {plan.child_id for plan in ExplorationPlan.query.all()} == {10, 11}


def test_database_failure_rolls_back_the_whole_batch(app, generation_db, monkeypatch):
    with app.app_context():
        data = seed_generation_context()

        def fail_commit():
            raise SQLAlchemyError("simulated commit failure")

        monkeypatch.setattr(db.session, "commit", fail_commit)
        assert_error(
            lambda: generate_exploration_plans_from_route(
                data["owner"],
                data["route"].id,
                data["child_a"].id,
                [data["first_stop"].id, data["second_stop"].id],
            ),
            "DATABASE_ERROR",
            500,
        )
        assert ExplorationPlan.query.count() == 0


def test_manual_null_route_stop_plan_remains_compatible(app, generation_db):
    with app.app_context():
        data = seed_generation_context()
        manual_plan = ExplorationPlan(
            user_id=data["owner"].id,
            child_id=data["child_a"].id,
            title="手动探索计划",
            destination="首都博物馆",
            age_group=data["child_a"].age_group,
            duration="半天",
            interests=["城市历史"],
            status="ready",
        )
        db.session.add(manual_plan)
        db.session.commit()

        assert (manual_plan.route_stop_id, manual_plan.source_snapshot) == (None, None)
