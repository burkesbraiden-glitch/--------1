from contextlib import contextmanager

import pytest
from flask_jwt_extended import create_access_token
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
    TaskSubmission,
    User,
)
from app.services.route_plan_generation import generate_exploration_plans_from_route


@pytest.fixture()
def plans_db(app):
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def auth_headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def create_user(user_id, phone):
    user = User(id=user_id, phone=phone, nickname="童旅用户")
    db.session.add(user)
    db.session.commit()
    return user


def create_child(child_id, user_id, age_group="7-12", is_default=True):
    child = Child(
        id=child_id,
        user_id=user_id,
        name="小小探索家",
        age=7 if age_group == "7-12" else 5,
        age_group=age_group,
        interests=[],
        is_default=is_default,
    )
    db.session.add(child)
    db.session.commit()
    return child


def create_plan(plan_id, user_id, child_id, status="ready", title="故宫亲子探索"):
    plan = ExplorationPlan(
        id=plan_id,
        user_id=user_id,
        child_id=child_id,
        title=title,
        destination="故宫博物院",
        age_group="7-12",
        duration="3小时",
        interests=["历史故事"],
        status=status,
    )
    db.session.add(plan)
    db.session.commit()
    return plan


def create_task(task_id, plan_id, order=1, title="找屋顶上的小兽"):
    task = Task(
        id=task_id,
        plan_id=plan_id,
        sort_order=order,
        title=title,
        subtitle="在屋顶上找一找那些小兽",
        age_group="7-12",
        duration="约10分钟",
        task_type="观察任务",
        summary="故宫屋顶上有一排可爱又神秘的小兽，快和孩子一起找一找吧！",
        objective="找到屋顶小兽，观察它们的排列",
        steps=["抬头看看屋檐边缘"],
        questions=["为什么它们站在屋顶上？"],
        record_mode="拍照片，或说出你最喜欢的一只并写下来。",
        theme="beasts",
    )
    db.session.add(task)
    db.session.commit()
    return task


def create_submission(submission_id, task_id, status="completed", note="", image_url=None):
    submission = TaskSubmission(
        id=submission_id,
        task_id=task_id,
        status=status,
        note=note,
        image_url=image_url,
    )
    db.session.add(submission)
    db.session.commit()
    return submission


def create_complete_task_set(plan_id, *, submission_statuses=("completed", "completed", "completed")):
    tasks = [
        create_task(1000, plan_id, order=1),
        create_task(1001, plan_id, order=2, title="拍一扇宫门"),
        create_task(1002, plan_id, order=3, title="讲一个故事"),
    ]
    for index, (task, status) in enumerate(zip(tasks, submission_statuses), start=1):
        create_submission(5000 + index, task.id, status=status)
    return tasks


def create_route_generated_plan(
    user,
    child,
    *,
    attraction_id=300,
    route_id=400,
    day_id=500,
    stop_id=600,
):
    attraction = Attraction(
        id=attraction_id,
        name="故宫博物院",
        city="北京",
        district="东城区",
        address="景山前街4号",
        summary="明清两代皇家宫殿",
        tags=["历史", "建筑"],
        recommended_duration_minutes=180,
        cover_image="https://example.test/forbidden-city.webp",
    )
    route = Route(
        id=route_id,
        user_id=user.id,
        title="北京文化探索路线",
        city="北京",
        status="ready",
    )
    day = RouteDay(
        id=day_id,
        route_id=route.id,
        day_number=1,
        title="第一天",
    )
    stop = RouteStop(
        id=stop_id,
        route_day_id=day.id,
        attraction_id=attraction.id,
        sort_order=1,
        note="先看午门",
    )
    db.session.add_all([attraction, route, day, stop])
    db.session.commit()

    with assign_sqlite_plan_ids():
        return generate_exploration_plans_from_route(user, route.id, child.id, [stop.id])


def valid_payload(**overrides):
    payload = {
        "title": "故宫亲子探索",
        "destination": "故宫博物院",
        "duration": "3小时",
        "interests": ["历史故事", " 古建筑 ", "历史故事"],
        "childId": 10,
        "ageGroup": "7-12",
    }
    payload.update(overrides)
    return payload


@contextmanager
def assign_sqlite_plan_ids():
    next_plan_id = 1000

    def assign_plan_id(mapper, connection, target):
        nonlocal next_plan_id
        if target.id is None:
            target.id = next_plan_id
            next_plan_id += 1

    event.listen(ExplorationPlan, "before_insert", assign_plan_id)
    try:
        yield
    finally:
        event.remove(ExplorationPlan, "before_insert", assign_plan_id)


def test_post_plan_requires_token(client):
    response = client.post("/api/v1/plans", json=valid_payload())

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_post_plan_uses_destination_title_when_title_is_omitted(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)

    payload = valid_payload(destination="故宫")
    payload.pop("title")

    with assign_sqlite_plan_ids():
        response = client.post(
            "/api/v1/plans",
            json=payload,
            headers=auth_headers(app, 1),
        )

    assert response.status_code == 201
    assert response.get_json()["data"]["plan"]["title"] == "故宫亲子探索"
    with app.app_context():
        assert ExplorationPlan.query.one().title == "故宫亲子探索"


def test_post_plan_uses_destination_title_when_title_is_blank(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)

    with assign_sqlite_plan_ids():
        response = client.post(
            "/api/v1/plans",
            json=valid_payload(title="   ", destination="颐和园"),
            headers=auth_headers(app, 1),
        )

    assert response.status_code == 201
    assert response.get_json()["data"]["plan"]["title"] == "颐和园亲子探索"
    with app.app_context():
        assert ExplorationPlan.query.one().title == "颐和园亲子探索"


def test_post_plan_uses_destination_title_when_title_is_empty_string(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)

    with assign_sqlite_plan_ids():
        response = client.post(
            "/api/v1/plans",
            json=valid_payload(title="", destination="天坛"),
            headers=auth_headers(app, 1),
        )

    assert response.status_code == 201
    assert response.get_json()["data"]["plan"]["title"] == "天坛亲子探索"
    with app.app_context():
        assert ExplorationPlan.query.one().title == "天坛亲子探索"


def test_post_plan_trims_custom_title_before_saving(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)

    with assign_sqlite_plan_ids():
        response = client.post(
            "/api/v1/plans",
            json=valid_payload(title="  第一次走进故宫  "),
            headers=auth_headers(app, 1),
        )

    assert response.status_code == 201
    assert response.get_json()["data"]["plan"]["title"] == "第一次走进故宫"
    with app.app_context():
        assert ExplorationPlan.query.one().title == "第一次走进故宫"


def test_post_plan_rejects_title_longer_than_120_without_side_effects(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        before_plan_count = ExplorationPlan.query.count()
        before_task_count = Task.query.count()

    with assign_sqlite_plan_ids():
        response = client.post(
            "/api/v1/plans",
            json=valid_payload(title="旅" * 121),
            headers=auth_headers(app, 1),
        )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"
    with app.app_context():
        assert ExplorationPlan.query.count() == before_plan_count
        assert Task.query.count() == before_task_count


def test_post_plan_applies_title_length_limit_after_trimming(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)

    with assign_sqlite_plan_ids():
        max_length_response = client.post(
            "/api/v1/plans",
            json=valid_payload(title="  " + ("旅" * 120) + "  "),
            headers=auth_headers(app, 1),
        )

    assert max_length_response.status_code == 201
    assert max_length_response.get_json()["data"]["plan"]["title"] == "旅" * 120
    with app.app_context():
        assert ExplorationPlan.query.one().title == "旅" * 120
        before_plan_count = ExplorationPlan.query.count()

    with assign_sqlite_plan_ids():
        over_limit_response = client.post(
            "/api/v1/plans",
            json=valid_payload(title="  " + ("旅" * 121) + "  "),
            headers=auth_headers(app, 1),
        )

    assert over_limit_response.status_code == 400
    assert over_limit_response.get_json()["error"]["code"] == "VALIDATION_ERROR"
    with app.app_context():
        assert ExplorationPlan.query.count() == before_plan_count


def test_post_plan_requires_destination(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post(
        "/api/v1/plans",
        json={"title": "故宫亲子探索", "duration": "3小时"},
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_plan_requires_duration(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post(
        "/api/v1/plans",
        json={"title": "故宫亲子探索", "destination": "故宫博物院"},
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_plan_rejects_bool_child_id(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post(
        "/api/v1/plans",
        json=valid_payload(childId=True),
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_plan_rejects_inconsistent_age_group(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1, age_group="7-12")

    response = client.post(
        "/api/v1/plans",
        json=valid_payload(ageGroup="3-6"),
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_plan_requires_existing_child(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post(
        "/api/v1/plans",
        json={"title": "故宫亲子探索", "destination": "故宫博物院", "duration": "3小时"},
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 409
    payload = response.get_json()
    assert payload["error"]["code"] == "CHILD_REQUIRED"


def test_post_plan_rejects_client_status_and_task_count(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)

    for forbidden in ("status", "taskCount"):
        response = client.post(
            "/api/v1/plans",
            json=valid_payload(**{forbidden: "bad"}),
            headers=auth_headers(app, 1),
        )
        assert response.status_code == 400
        assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_plan_success_returns_ready_and_task_count_zero(client, app, plans_db, monkeypatch):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)

    def fake_create_plan(user, payload):
        assert user.id == 1
        assert payload["childId"] == 10
        return {
            "id": 99,
            "title": "故宫亲子探索",
            "destination": "故宫博物院",
            "ageGroup": "7-12",
            "duration": "3小时",
            "taskCount": 0,
            "interests": ["历史故事", "古建筑"],
            "status": "ready",
            "childId": 10,
            "createdAt": "2026-07-09T00:00:00Z",
            "updatedAt": "2026-07-09T00:00:00Z",
        }

    monkeypatch.setattr("app.api.v1.plans.create_plan", fake_create_plan)

    response = client.post("/api/v1/plans", json=valid_payload(), headers=auth_headers(app, 1))

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["message"] == "Plan created"
    plan = payload["data"]["plan"]
    assert plan["status"] == "ready"
    assert plan["taskCount"] == 0
    assert "user_id" not in plan
    assert "taskIds" not in plan


def test_get_plans_requires_token(client):
    response = client.get("/api/v1/plans")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_get_plans_returns_current_user_only(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_user(2, "13800138001")
        create_child(10, 1)
        create_child(20, 2)
        create_plan(100, 1, 10)
        create_plan(200, 2, 20)

    response = client.get("/api/v1/plans", headers=auth_headers(app, 1))

    assert response.status_code == 200
    plans = response.get_json()["data"]["plans"]
    assert [plan["id"] for plan in plans] == [100]
    assert plans[0]["taskCount"] == 0
    assert "user_id" not in plans[0]


def test_get_plans_returns_dynamic_task_count_without_cross_user_leak(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_user(2, "13800138001")
        create_child(10, 1)
        create_child(20, 2)
        create_plan(100, 1, 10)
        create_plan(101, 1, 10, title="国家博物馆亲子探索")
        create_plan(200, 2, 20)
        create_task(1000, 100, order=1)
        create_task(1001, 100, order=2, title="拍一扇宫门")
        create_task(2000, 200, order=1)

    response = client.get("/api/v1/plans", headers=auth_headers(app, 1))

    assert response.status_code == 200
    task_counts = {plan["id"]: plan["taskCount"] for plan in response.get_json()["data"]["plans"]}
    assert task_counts == {100: 2, 101: 0}


def test_get_plans_projects_route_generated_plan_source_and_empty_progress(client, app, plans_db):
    with app.app_context():
        user = create_user(1, "13800138000")
        child = create_child(10, user.id)
        create_route_generated_plan(user, child)

    response = client.get("/api/v1/plans", headers=auth_headers(app, 1))

    assert response.status_code == 200
    plan = response.get_json()["data"]["plans"][0]
    assert plan["routeStopId"] == 600
    assert plan["sourceSnapshot"] == {
        "schemaVersion": 1,
        "route": {
            "id": 400,
            "title": "北京文化探索路线",
            "city": "北京",
            "startDate": None,
            "endDate": None,
        },
        "day": {
            "id": 500,
            "dayNumber": 1,
            "date": None,
            "title": "第一天",
        },
        "stop": {
            "id": 600,
            "sortOrder": 1,
            "note": "先看午门",
        },
        "attraction": {
            "id": 300,
            "name": "故宫博物院",
            "city": "北京",
            "district": "东城区",
            "address": "景山前街4号",
            "summary": "明清两代皇家宫殿",
            "tags": ["历史", "建筑"],
            "recommendedDurationMinutes": 180,
            "coverImage": "https://example.test/forbidden-city.webp",
        },
    }
    assert plan["progress"] == {"total": 0, "completed": 0}


def test_get_plan_detail_projects_manual_plan_with_null_source(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10)

    response = client.get("/api/v1/plans/100", headers=auth_headers(app, 1))

    assert response.status_code == 200
    plan = response.get_json()["data"]["plan"]
    assert plan["routeStopId"] is None
    assert plan["sourceSnapshot"] is None


def test_get_plan_detail_projects_completed_task_progress(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10)
        create_task(1000, 100, order=1)
        create_task(1001, 100, order=2, title="拍一扇宫门")
        create_task(1002, 100, order=3, title="讲一个故事")
        create_submission(5001, 1000, status="completed")
        create_submission(5002, 1001, status="completed")

    response = client.get("/api/v1/plans/100", headers=auth_headers(app, 1))

    assert response.status_code == 200
    assert response.get_json()["data"]["plan"]["progress"] == {
        "total": 3,
        "completed": 2,
    }


def test_get_plans_projection_has_no_task_or_record_side_effects(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10)
        create_task(1000, 100, order=1)
        create_submission(5001, 1000, status="in-progress")
        db.session.add(
            GuideCard(
                id=700,
                plan_id=100,
                child_intro=["一起探索"],
                questions=["你看到了什么？"],
                focus_items=["宫门"],
            )
        )
        db.session.add(JourneyRecord(id=800, plan_id=100, status="draft"))
        db.session.commit()
        before = {
            "tasks": Task.query.count(),
            "submissions": TaskSubmission.query.count(),
            "guides": GuideCard.query.count(),
            "records": JourneyRecord.query.count(),
        }

    response = client.get("/api/v1/plans", headers=auth_headers(app, 1))

    assert response.status_code == 200
    with app.app_context():
        after = {
            "tasks": Task.query.count(),
            "submissions": TaskSubmission.query.count(),
            "guides": GuideCard.query.count(),
            "records": JourneyRecord.query.count(),
        }
    assert after == before


def test_get_plans_does_not_expose_other_users_route_plan_source(client, app, plans_db):
    with app.app_context():
        user_a = create_user(1, "13800138000")
        user_b = create_user(2, "13800138001")
        user_a_id = user_a.id
        child_a = create_child(10, user_a.id)
        child_b = create_child(20, user_b.id)
        create_plan(100, user_a.id, child_a.id)
        create_route_generated_plan(
            user_b,
            child_b,
            attraction_id=301,
            route_id=401,
            day_id=501,
            stop_id=601,
        )

    response = client.get("/api/v1/plans", headers=auth_headers(app, user_a_id))

    assert response.status_code == 200
    plans = response.get_json()["data"]["plans"]
    assert [plan["id"] for plan in plans] == [100]
    assert plans[0]["routeStopId"] is None
    assert plans[0]["sourceSnapshot"] is None


def test_get_plan_detail_not_found_for_missing_or_other_user(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_user(2, "13800138001")
        create_child(20, 2)
        create_plan(200, 2, 20)

    missing = client.get("/api/v1/plans/999", headers=auth_headers(app, 1))
    other_user = client.get("/api/v1/plans/200", headers=auth_headers(app, 1))

    assert missing.status_code == 404
    assert missing.get_json()["error"]["code"] == "PLAN_NOT_FOUND"
    assert other_user.status_code == 404
    assert other_user.get_json()["error"]["code"] == "PLAN_NOT_FOUND"


def test_get_plan_detail_returns_dynamic_task_count(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10)
        create_task(1000, 100, order=1)
        create_task(1001, 100, order=2, title="拍一扇宫门")
        create_task(1002, 100, order=3, title="讲一个故事")

    response = client.get("/api/v1/plans/100", headers=auth_headers(app, 1))

    assert response.status_code == 200
    assert response.get_json()["data"]["plan"]["taskCount"] == 3


def test_patch_plan_rejects_empty_object(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10)

    response = client.patch("/api/v1/plans/100", json={}, headers=auth_headers(app, 1))

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("field", ["unknown", "childId", "status", "taskCount"])
def test_patch_plan_rejects_unknown_or_forbidden_fields(client, app, plans_db, field):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10)

    response = client.patch(
        "/api/v1/plans/100",
        json={field: "bad"},
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_patch_plan_success_does_not_change_status(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, status="in-progress")

    response = client.patch(
        "/api/v1/plans/100",
        json={"title": "更新后的计划", "destination": "国家博物馆", "interests": [" 文物 ", "文物"]},
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 200
    plan = response.get_json()["data"]["plan"]
    assert plan["title"] == "更新后的计划"
    assert plan["destination"] == "国家博物馆"
    assert plan["interests"] == ["文物"]
    assert plan["status"] == "in-progress"


def test_patch_plan_returns_dynamic_task_count(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10)
        create_task(1000, 100, order=1)

    response = client.patch(
        "/api/v1/plans/100",
        json={"title": "更新后的计划"},
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["plan"]["taskCount"] == 1


def test_patch_other_users_plan_returns_not_found(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_user(2, "13800138001")
        create_child(20, 2)
        create_plan(200, 2, 20)

    response = client.patch(
        "/api/v1/plans/200",
        json={"title": "越权修改"},
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "PLAN_NOT_FOUND"


def test_start_ready_plan_changes_to_in_progress(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, status="ready")

    response = client.post("/api/v1/plans/100/start", headers=auth_headers(app, 1))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["message"] == "Exploration started"
    assert payload["data"]["plan"]["status"] == "in-progress"


def test_start_plan_returns_dynamic_task_count(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, status="ready")
        create_task(1000, 100, order=1)
        create_task(1001, 100, order=2, title="拍一扇宫门")

    response = client.post("/api/v1/plans/100/start", headers=auth_headers(app, 1))

    assert response.status_code == 200
    assert response.get_json()["data"]["plan"]["taskCount"] == 2


def test_start_in_progress_plan_is_idempotent(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, status="in-progress")

    response = client.post("/api/v1/plans/100/start", headers=auth_headers(app, 1))

    assert response.status_code == 200
    assert response.get_json()["data"]["plan"]["id"] == 100
    assert response.get_json()["data"]["plan"]["status"] == "in-progress"


@pytest.mark.parametrize(
    ("status", "code"),
    [("draft", "PLAN_NOT_READY"), ("completed", "PLAN_ALREADY_COMPLETED")],
)
def test_start_plan_rejects_invalid_status(client, app, plans_db, status, code):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, status=status)

    response = client.post("/api/v1/plans/100/start", headers=auth_headers(app, 1))

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == code


def test_start_other_users_plan_returns_not_found(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_user(2, "13800138001")
        create_child(20, 2)
        create_plan(200, 2, 20)

    response = client.post("/api/v1/plans/200/start", headers=auth_headers(app, 1))

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "PLAN_NOT_FOUND"


def test_plan_serialization_includes_null_completed_at(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, status="in-progress")

    response = client.get("/api/v1/plans/100", headers=auth_headers(app, 1))

    assert response.status_code == 200
    assert response.get_json()["data"]["plan"]["completedAt"] is None


@pytest.mark.parametrize(
    ("status", "code"),
    [("draft", "PLAN_NOT_READY"), ("ready", "PLAN_NOT_STARTED")],
)
def test_complete_plan_rejects_not_started_statuses(client, app, plans_db, status, code):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, status=status)

    response = client.post("/api/v1/plans/100/complete", headers=auth_headers(app, 1))

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == code


@pytest.mark.parametrize("task_count", [0, 1, 2])
def test_complete_plan_requires_the_full_task_set(client, app, plans_db, task_count):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, status="in-progress")
        for task_id in range(1000, 1000 + task_count):
            create_task(task_id, 100, order=task_id - 999)

    response = client.post("/api/v1/plans/100/complete", headers=auth_headers(app, 1))

    assert response.status_code == 409
    error = response.get_json()["error"]
    assert error["code"] == "PLAN_TASKS_INCOMPLETE"
    assert error["details"] == {
        "expectedTaskCount": 3,
        "taskCount": task_count,
        "completedTaskCount": 0,
        "missingSubmissionTaskIds": list(range(1000, 1000 + task_count)),
        "incompleteTaskIds": [],
    }


def test_complete_plan_rejects_task_without_submission(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, status="in-progress")
        create_task(1000, 100, order=1)
        create_task(1001, 100, order=2, title="拍一扇宫门")
        create_task(1002, 100, order=3, title="讲一个故事")
        create_submission(5001, 1000)
        create_submission(5002, 1001)

    response = client.post("/api/v1/plans/100/complete", headers=auth_headers(app, 1))

    assert response.status_code == 409
    assert response.get_json()["error"] == {
        "code": "PLAN_TASKS_INCOMPLETE",
        "message": "Plan tasks are incomplete",
        "details": {
            "expectedTaskCount": 3,
            "taskCount": 3,
            "completedTaskCount": 2,
            "missingSubmissionTaskIds": [1002],
            "incompleteTaskIds": [],
        },
    }


def test_complete_plan_rejects_in_progress_submission(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, status="in-progress")
        create_complete_task_set(100, submission_statuses=("completed", "in-progress", "completed"))

    response = client.post("/api/v1/plans/100/complete", headers=auth_headers(app, 1))

    assert response.status_code == 409
    assert response.get_json()["error"]["details"] == {
        "expectedTaskCount": 3,
        "taskCount": 3,
        "completedTaskCount": 2,
        "missingSubmissionTaskIds": [],
        "incompleteTaskIds": [1001],
    }


def test_complete_plan_completes_all_submitted_tasks_without_note_or_image(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, status="in-progress")
        create_complete_task_set(100)

    response = client.post("/api/v1/plans/100/complete", headers=auth_headers(app, 1))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["message"] == "Exploration completed"
    assert payload["data"]["completedNow"] is True
    assert payload["data"]["plan"]["status"] == "completed"
    assert payload["data"]["plan"]["completedAt"] is not None
    with app.app_context():
        plan = db.session.get(ExplorationPlan, 100)
        assert plan.status == "completed"
        assert plan.completed_at is not None


def test_complete_plan_is_idempotent_and_keeps_completed_at(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, status="in-progress")
        create_complete_task_set(100)

    first = client.post("/api/v1/plans/100/complete", headers=auth_headers(app, 1))
    second = client.post("/api/v1/plans/100/complete", headers=auth_headers(app, 1))

    assert first.status_code == second.status_code == 200
    assert first.get_json()["data"]["completedNow"] is True
    assert second.get_json()["message"] == "Exploration already completed"
    assert second.get_json()["data"]["completedNow"] is False
    assert second.get_json()["data"]["plan"]["completedAt"] == first.get_json()["data"]["plan"]["completedAt"]


def test_complete_plan_hides_other_users_plan(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_user(2, "13800138001")
        create_child(10, 1)
        create_child(20, 2)
        create_plan(200, 2, 20, status="in-progress")
        create_complete_task_set(200)

    response = client.post("/api/v1/plans/200/complete", headers=auth_headers(app, 1))

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "PLAN_NOT_FOUND"


def test_patch_completed_plan_is_locked(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, status="completed")

    response = client.patch("/api/v1/plans/100", json={"title": "不应修改"}, headers=auth_headers(app, 1))

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "PLAN_ALREADY_COMPLETED"
    with app.app_context():
        assert db.session.get(ExplorationPlan, 100).title == "故宫亲子探索"


def test_complete_plan_rolls_back_when_commit_fails(client, app, plans_db, monkeypatch):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, status="in-progress")
        create_complete_task_set(100)

    def fail_commit():
        raise SQLAlchemyError("commit failed")

    monkeypatch.setattr(db.session, "commit", fail_commit)

    response = client.post("/api/v1/plans/100/complete", headers=auth_headers(app, 1))

    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "DATABASE_ERROR"
    with app.app_context():
        plan = db.session.get(ExplorationPlan, 100)
        assert plan.status == "in-progress"
        assert plan.completed_at is None
