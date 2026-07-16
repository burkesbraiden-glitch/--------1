from datetime import timedelta

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Child, ExplorationPlan, Task, TaskSubmission, User
from app.utils.time import utc_now


@pytest.fixture()
def submissions_db(app):
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


def create_plan(plan_id, user_id, child_id, *, status="in-progress", destination="故宫博物院"):
    plan = ExplorationPlan(
        id=plan_id,
        user_id=user_id,
        child_id=child_id,
        title=f"{destination}亲子探索",
        destination=destination,
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
        steps=["抬头看看屋檐边缘", "数一数有几只"],
        questions=["为什么它们站在屋顶上？"],
        record_mode="拍照片，或说出你最喜欢的一只并写下来。",
        theme="beasts",
    )
    db.session.add(task)
    db.session.commit()
    return task


def create_submission(
    task_id,
    *,
    submission_id=5000,
    status="in-progress",
    note="旧记录",
    completed_at=None,
    image_url=None,
):
    submission = TaskSubmission(
        id=submission_id,
        task_id=task_id,
        status=status,
        image_url=image_url,
        note=note,
        completed_at=completed_at,
    )
    db.session.add(submission)
    db.session.commit()
    return submission


def setup_task(app, *, plan_status="in-progress"):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, status=plan_status)
        create_task(1000, 100)
    return auth_headers(app, 1)


def task_path(suffix=""):
    return f"/api/v1/plans/100/tasks/1000/submission{suffix}"


def assert_error(response, status, code):
    assert response.status_code == status
    assert response.get_json()["error"]["code"] == code


def test_start_requires_token(client):
    response = client.post(task_path("/start"))

    assert_error(response, 401, "UNAUTHORIZED")


def test_start_returns_not_found_for_missing_or_unauthorized_plan(client, app, submissions_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_user(2, "13800138001")
        create_child(10, 1)
        create_plan(100, 1, 10)
        create_task(1000, 100)

    missing = client.post(
        "/api/v1/plans/999/tasks/1000/submission/start",
        headers=auth_headers(app, 1),
    )
    other_user = client.post(task_path("/start"), headers=auth_headers(app, 2))

    assert_error(missing, 404, "PLAN_NOT_FOUND")
    assert_error(other_user, 404, "PLAN_NOT_FOUND")


def test_start_returns_task_not_found_for_missing_or_other_plan_task(client, app, submissions_db):
    headers = setup_task(app)
    with app.app_context():
        create_plan(101, 1, 10, destination="国家博物馆")
        create_task(1001, 101, title="拍一扇宫门")

    missing = client.post(
        "/api/v1/plans/100/tasks/9999/submission/start",
        headers=headers,
    )
    other_plan = client.post(
        "/api/v1/plans/100/tasks/1001/submission/start",
        headers=headers,
    )

    assert_error(missing, 404, "TASK_NOT_FOUND")
    assert_error(other_plan, 404, "TASK_NOT_FOUND")


@pytest.mark.parametrize(
    ("plan_status", "code"),
    [
        ("draft", "PLAN_NOT_READY"),
        ("ready", "PLAN_NOT_STARTED"),
        ("completed", "PLAN_ALREADY_COMPLETED"),
    ],
)
def test_start_rejects_plan_statuses_that_are_not_in_progress(client, app, submissions_db, plan_status, code):
    headers = setup_task(app, plan_status=plan_status)

    response = client.post(task_path("/start"), headers=headers)

    assert_error(response, 409, code)


def test_start_creates_in_progress_submission_and_is_idempotent(client, app, submissions_db):
    headers = setup_task(app)

    first = client.post(task_path("/start"), headers=headers)
    second = client.post(task_path("/start"), headers=headers)

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.get_json()["message"] == "Task started"
    assert second.get_json()["message"] == "Task started"
    assert first.get_json()["data"]["task"]["status"] == "in-progress"
    assert second.get_json()["data"]["task"]["status"] == "in-progress"
    assert second.get_json()["data"]["task"]["record"] == {"imageUrl": None, "note": ""}
    with app.app_context():
        submissions = TaskSubmission.query.all()
        assert len(submissions) == 1
        assert submissions[0].status == "in-progress"
        assert submissions[0].image_url is None
        assert submissions[0].completed_at is None


def test_start_rejects_completed_task_without_reverting_status(client, app, submissions_db):
    headers = setup_task(app)
    completed_at = utc_now() - timedelta(minutes=5)
    with app.app_context():
        create_submission(1000, status="completed", note="已经完成", completed_at=completed_at)

    response = client.post(task_path("/start"), headers=headers)

    assert_error(response, 409, "TASK_ALREADY_COMPLETED")
    with app.app_context():
        submission = TaskSubmission.query.filter_by(task_id=1000).one()
        assert submission.status == "completed"
        assert submission.completed_at == completed_at


def test_patch_requires_token(client):
    response = client.patch(task_path(), json={"note": "发现了屋顶小兽"})

    assert_error(response, 401, "UNAUTHORIZED")


@pytest.mark.parametrize("payload", [{}, {"extra": "x"}, {"imageUrl": "https://x"}, {"imagePath": "/tmp/a.jpg"}])
def test_patch_rejects_empty_unknown_and_image_fields(client, app, submissions_db, payload):
    headers = setup_task(app)

    response = client.patch(task_path(), json=payload, headers=headers)

    assert_error(response, 400, "VALIDATION_ERROR")


@pytest.mark.parametrize("note", [None, 123, True, [], {}])
def test_patch_rejects_non_string_note(client, app, submissions_db, note):
    headers = setup_task(app)

    response = client.patch(task_path(), json={"note": note}, headers=headers)

    assert_error(response, 400, "VALIDATION_ERROR")


def test_patch_rejects_note_longer_than_2000_characters(client, app, submissions_db):
    headers = setup_task(app)

    response = client.patch(task_path(), json={"note": "童" * 2001}, headers=headers)

    assert_error(response, 400, "VALIDATION_ERROR")


def test_patch_creates_in_progress_submission_for_not_started_task(client, app, submissions_db):
    headers = setup_task(app)

    response = client.patch(task_path(), json={"note": "  第一行\n  第二行  "}, headers=headers)

    assert response.status_code == 200
    task = response.get_json()["data"]["task"]
    assert task["status"] == "in-progress"
    assert task["record"] == {"imageUrl": None, "note": "第一行\n  第二行"}
    assert task["completedAt"] is None
    with app.app_context():
        submission = TaskSubmission.query.filter_by(task_id=1000).one()
        assert submission.status == "in-progress"
        assert submission.note == "第一行\n  第二行"
        assert submission.image_url is None


def test_patch_updates_existing_in_progress_submission_without_creating_duplicate(client, app, submissions_db):
    headers = setup_task(app)
    with app.app_context():
        create_submission(1000, note="旧记录", image_url="task-images/existing.png")

    response = client.patch(task_path(), json={"note": ""}, headers=headers)

    assert response.status_code == 200
    task = response.get_json()["data"]["task"]
    assert task["status"] == "in-progress"
    assert task["record"]["note"] == ""
    assert task["record"]["imageUrl"] == "/api/v1/plans/100/tasks/1000/submission/image"
    with app.app_context():
        assert TaskSubmission.query.count() == 1
        submission = TaskSubmission.query.filter_by(task_id=1000).one()
        assert submission.note == ""
        assert submission.image_url == "task-images/existing.png"


def test_patch_completed_task_updates_note_without_changing_completed_at(client, app, submissions_db):
    headers = setup_task(app)
    completed_at = utc_now() - timedelta(minutes=5)
    with app.app_context():
        create_submission(1000, status="completed", note="旧记录", completed_at=completed_at)

    response = client.patch(task_path(), json={"note": "完成后修正"}, headers=headers)

    assert response.status_code == 200
    task = response.get_json()["data"]["task"]
    assert task["status"] == "completed"
    assert task["record"]["note"] == "完成后修正"
    assert task["completedAt"] == f"{completed_at.isoformat()}Z"
    with app.app_context():
        submission = TaskSubmission.query.filter_by(task_id=1000).one()
        assert submission.completed_at == completed_at


def test_complete_requires_token(client):
    response = client.post(task_path("/complete"), json={})

    assert_error(response, 401, "UNAUTHORIZED")


@pytest.mark.parametrize("payload", [{"imageUrl": "https://x"}, {"imagePath": "/tmp/a.jpg"}, {"status": "completed"}])
def test_complete_rejects_unknown_and_image_fields(client, app, submissions_db, payload):
    headers = setup_task(app)

    response = client.post(task_path("/complete"), json=payload, headers=headers)

    assert_error(response, 400, "VALIDATION_ERROR")


def test_complete_creates_completed_submission_for_empty_body(client, app, submissions_db):
    headers = setup_task(app)

    response = client.post(task_path("/complete"), headers=headers)

    assert response.status_code == 200
    task = response.get_json()["data"]["task"]
    assert task["status"] == "completed"
    assert task["record"] == {"imageUrl": None, "note": ""}
    assert task["completedAt"] is not None
    with app.app_context():
        submission = TaskSubmission.query.filter_by(task_id=1000).one()
        assert submission.status == "completed"
        assert submission.note == ""
        assert submission.image_url is None
        assert submission.completed_at is not None


def test_complete_updates_in_progress_submission_and_can_save_note(client, app, submissions_db):
    headers = setup_task(app)
    with app.app_context():
        create_submission(1000, note="旧记录", image_url="task-images/existing.png")

    response = client.post(task_path("/complete"), json={"note": " 最终记录 "}, headers=headers)

    assert response.status_code == 200
    task = response.get_json()["data"]["task"]
    assert task["status"] == "completed"
    assert task["record"]["note"] == "最终记录"
    assert task["record"]["imageUrl"] == "/api/v1/plans/100/tasks/1000/submission/image"
    with app.app_context():
        assert TaskSubmission.query.count() == 1
        submission = TaskSubmission.query.filter_by(task_id=1000).one()
        assert submission.status == "completed"
        assert submission.note == "最终记录"
        assert submission.image_url == "task-images/existing.png"
        assert submission.completed_at is not None


def test_complete_is_idempotent_and_keeps_completed_at_stable(client, app, submissions_db):
    headers = setup_task(app)
    completed_at = utc_now() - timedelta(minutes=5)
    with app.app_context():
        create_submission(1000, status="completed", note="旧记录", completed_at=completed_at)

    response = client.post(task_path("/complete"), json={"note": "重复完成可改文字"}, headers=headers)

    assert response.status_code == 200
    task = response.get_json()["data"]["task"]
    assert task["status"] == "completed"
    assert task["record"]["note"] == "重复完成可改文字"
    assert task["completedAt"] == f"{completed_at.isoformat()}Z"
    with app.app_context():
        assert TaskSubmission.query.count() == 1
        submission = TaskSubmission.query.filter_by(task_id=1000).one()
        assert submission.completed_at == completed_at


def test_get_tasks_and_detail_reflect_submission_writes_immediately(client, app, submissions_db):
    headers = setup_task(app)

    client.patch(task_path(), json={"note": "我发现屋檐有小兽"}, headers=headers)
    list_response = client.get("/api/v1/plans/100/tasks", headers=headers)
    detail_response = client.get("/api/v1/plans/100/tasks/1000", headers=headers)

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    list_task = list_response.get_json()["data"]["tasks"][0]
    detail_task = detail_response.get_json()["data"]["task"]
    assert list_task["status"] == "in-progress"
    assert detail_task["status"] == "in-progress"
    assert list_task["record"] == {"imageUrl": None, "note": "我发现屋檐有小兽"}
    assert detail_task["record"] == {"imageUrl": None, "note": "我发现屋檐有小兽"}


def test_completing_all_tasks_does_not_complete_plan(client, app, submissions_db):
    headers = setup_task(app)
    with app.app_context():
        create_task(1001, 100, order=2, title="拍一扇宫门")
        create_task(1002, 100, order=3, title="讲一个故事")

    for task_id in (1000, 1001, 1002):
        response = client.post(
            f"/api/v1/plans/100/tasks/{task_id}/submission/complete",
            headers=headers,
        )
        assert response.status_code == 200

    plan_response = client.get("/api/v1/plans/100", headers=headers)

    assert plan_response.status_code == 200
    assert plan_response.get_json()["data"]["plan"]["status"] == "in-progress"
    with app.app_context():
        assert TaskSubmission.query.count() == 3
