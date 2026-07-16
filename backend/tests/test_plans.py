import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Child, ExplorationPlan, Task, User


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


def test_post_plan_requires_token(client):
    response = client.post("/api/v1/plans", json=valid_payload())

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_post_plan_requires_title(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post(
        "/api/v1/plans",
        json={"destination": "故宫博物院", "duration": "3小时"},
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_plan_rejects_blank_title(client, app, plans_db):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post(
        "/api/v1/plans",
        json=valid_payload(title="   "),
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


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
