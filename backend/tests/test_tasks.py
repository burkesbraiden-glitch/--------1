import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Child, ExplorationPlan, Task, TaskSubmission, User
from app.services.task_generator import generate_task_definitions


@pytest.fixture()
def tasks_db(app):
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


def create_child(child_id, user_id, age_group="7-12"):
    child = Child(
        id=child_id,
        user_id=user_id,
        name="小小探索家",
        age=7 if age_group == "7-12" else 5,
        age_group=age_group,
        interests=[],
        is_default=True,
    )
    db.session.add(child)
    db.session.commit()
    return child


def create_plan(
    plan_id,
    user_id,
    child_id,
    *,
    status="ready",
    destination="故宫博物院",
    age_group="7-12",
    interests=None,
):
    plan = ExplorationPlan(
        id=plan_id,
        user_id=user_id,
        child_id=child_id,
        title=f"{destination}亲子探索",
        destination=destination,
        age_group=age_group,
        duration="3小时",
        interests=interests or ["历史故事"],
        status=status,
    )
    db.session.add(plan)
    db.session.commit()
    return plan


def create_task(task_id, plan_id, order=1, age_group="7-12", title="找屋顶上的小兽"):
    task = Task(
        id=task_id,
        plan_id=plan_id,
        sort_order=order,
        title=title,
        subtitle="在屋顶上找一找那些小兽",
        age_group=age_group,
        duration="约10分钟",
        task_type="观察任务",
        summary="故宫屋顶上有一排可爱又神秘的小兽，快和孩子一起找一找吧！",
        objective="找到屋顶小兽，观察它们的排列",
        steps=["抬头看看屋檐边缘", "数一数有几只", "留意最大的那一只在哪里"],
        questions=["为什么它们站在屋顶上？", "你觉得它们在守护什么？"],
        record_mode="拍照片，或说出你最喜欢的一只并写下来。",
        theme="beasts",
    )
    db.session.add(task)
    db.session.commit()
    return task


def test_get_tasks_requires_token(client):
    response = client.get("/api/v1/plans/100/tasks")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_get_tasks_missing_plan_returns_plan_not_found(client, app, tasks_db):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.get("/api/v1/plans/999/tasks", headers=auth_headers(app, 1))

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "PLAN_NOT_FOUND"


def test_other_user_cannot_list_or_generate_tasks(client, app, tasks_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_user(2, "13800138001")
        create_child(10, 1)
        create_plan(100, 1, 10)

    get_response = client.get("/api/v1/plans/100/tasks", headers=auth_headers(app, 2))
    post_response = client.post("/api/v1/plans/100/tasks/generate", headers=auth_headers(app, 2))

    assert get_response.status_code == 404
    assert get_response.get_json()["error"]["code"] == "PLAN_NOT_FOUND"
    assert post_response.status_code == 404
    assert post_response.get_json()["error"]["code"] == "PLAN_NOT_FOUND"


def test_get_empty_tasks_returns_empty_without_creating(client, app, tasks_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10)

    response = client.get("/api/v1/plans/100/tasks", headers=auth_headers(app, 1))

    assert response.status_code == 200
    assert response.get_json()["data"] == {"tasks": [], "taskCount": 0}
    with app.app_context():
        assert Task.query.count() == 0


def test_generate_requires_token(client):
    response = client.post("/api/v1/plans/100/tasks/generate")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_generate_missing_plan_returns_plan_not_found(client, app, tasks_db):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post("/api/v1/plans/999/tasks/generate", headers=auth_headers(app, 1))

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "PLAN_NOT_FOUND"


@pytest.mark.parametrize(
    ("status", "code"),
    [("draft", "PLAN_NOT_READY"), ("completed", "PLAN_ALREADY_COMPLETED")],
)
def test_generate_rejects_invalid_plan_status(client, app, tasks_db, status, code):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, status=status)

    response = client.post("/api/v1/plans/100/tasks/generate", headers=auth_headers(app, 1))

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == code


@pytest.mark.parametrize("status", ["ready", "in-progress"])
def test_generate_creates_three_tasks_for_allowed_statuses(client, app, tasks_db, status):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, status=status, age_group="7-12")

    response = client.post("/api/v1/plans/100/tasks/generate", headers=auth_headers(app, 1))

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["message"] == "Tasks generated"
    tasks = payload["data"]["tasks"]
    assert payload["data"]["taskCount"] == 3
    assert [task["order"] for task in tasks] == [1, 2, 3]
    assert [task["ageGroup"] for task in tasks] == ["7-12", "7-12", "7-12"]
    assert tasks[0]["title"] == "找屋顶上的小兽"
    assert tasks[0]["status"] == "not-started"
    assert tasks[0]["record"] == {"imageUrl": None, "note": ""}
    assert tasks[0]["completedAt"] is None
    assert "sort_order" not in tasks[0]
    assert "submissionId" not in tasks[0]
    with app.app_context():
        assert Task.query.count() == 3
        assert TaskSubmission.query.count() == 0


def test_generate_is_idempotent_for_existing_complete_task_set(client, app, tasks_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10)

    first = client.post("/api/v1/plans/100/tasks/generate", headers=auth_headers(app, 1))
    second = client.post("/api/v1/plans/100/tasks/generate", headers=auth_headers(app, 1))

    assert first.status_code == 201
    assert second.status_code == 200
    first_tasks = first.get_json()["data"]["tasks"]
    second_tasks = second.get_json()["data"]["tasks"]
    assert [task["id"] for task in second_tasks] == [task["id"] for task in first_tasks]
    assert second_tasks[0]["title"] == first_tasks[0]["title"]
    with app.app_context():
        assert Task.query.count() == 3


def test_generate_rejects_existing_incomplete_task_set(client, app, tasks_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10)
        create_task(1000, 100, order=1)
        create_task(1001, 100, order=2, title="拍一扇宫门")

    response = client.post("/api/v1/plans/100/tasks/generate", headers=auth_headers(app, 1))

    assert response.status_code == 409
    error = response.get_json()["error"]
    assert error["code"] == "TASK_SET_INCOMPLETE"
    assert error["details"] == {"expectedCount": 3, "actualCount": 2}


def test_get_task_detail_returns_same_structure_and_submission_record(client, app, tasks_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10)
        task = create_task(1000, 100)
        submission = TaskSubmission(
            id=5000,
            task_id=task.id,
            status="completed",
            image_url="task-images/8f1998c0c8324a68bc52a21c48019831.png",
            note="红色的门很高，门钉排得很整齐。",
        )
        db.session.add(submission)
        db.session.commit()

    response = client.get("/api/v1/plans/100/tasks/1000", headers=auth_headers(app, 1))

    assert response.status_code == 200
    task = response.get_json()["data"]["task"]
    assert task["id"] == 1000
    assert task["planId"] == 100
    assert task["status"] == "completed"
    assert task["record"] == {
        "imageUrl": "/api/v1/plans/100/tasks/1000/submission/image",
        "note": "红色的门很高，门钉排得很整齐。",
    }
    assert task["completedAt"] is None
    assert "image_url" not in task
    assert "submissionId" not in task


def test_get_task_detail_not_found_for_missing_or_other_plan_task(client, app, tasks_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10)
        create_plan(101, 1, 10, destination="国家博物馆")
        create_task(1000, 101)

    missing = client.get("/api/v1/plans/100/tasks/9999", headers=auth_headers(app, 1))
    other_plan = client.get("/api/v1/plans/100/tasks/1000", headers=auth_headers(app, 1))

    assert missing.status_code == 404
    assert missing.get_json()["error"]["code"] == "TASK_NOT_FOUND"
    assert other_plan.status_code == 404
    assert other_plan.get_json()["error"]["code"] == "TASK_NOT_FOUND"


def test_other_user_cannot_read_task_detail(client, app, tasks_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_user(2, "13800138001")
        create_child(10, 1)
        create_plan(100, 1, 10)
        create_task(1000, 100)

    response = client.get("/api/v1/plans/100/tasks/1000", headers=auth_headers(app, 2))

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "PLAN_NOT_FOUND"


def test_palace_generator_preserves_frontend_template(app):
    with app.app_context():
        plan = ExplorationPlan(
            destination="故宫博物院",
            age_group="7-12",
            interests=["古建筑", "历史故事"],
        )

    tasks = generate_task_definitions(plan)

    assert len(tasks) == 3
    assert [task["sort_order"] for task in tasks] == [1, 2, 3]
    assert tasks[0]["title"] == "找屋顶上的小兽"
    assert tasks[1]["title"] == "拍一扇宫门"
    assert tasks[2]["title"] == "讲一个故事"
    assert tasks[1]["record_mode"] == "拍下宫门照片，写一句你发现的细节。"
    assert all(task["age_group"] == "7-12" for task in tasks)
    assert all("status" not in task and "record" not in task for task in tasks)


def test_fallback_generator_returns_stable_destination_specific_tasks(app):
    with app.app_context():
        plan = ExplorationPlan(
            destination="国家博物馆",
            age_group="3-6",
            interests=["颜色", "文物"],
        )

    first = generate_task_definitions(plan)
    second = generate_task_definitions(plan)

    assert first == second
    assert len(first) == 3
    assert first[0]["age_group"] == "3-6"
    assert "国家博物馆" in first[0]["summary"]
    assert "颜色、文物" in first[1]["questions"][0]
    assert all("image_url" not in task and "note" not in task for task in first)
