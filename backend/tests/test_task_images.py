from datetime import timedelta
from io import BytesIO
import os
import re

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Child, ExplorationPlan, JourneyRecord, Task, TaskSubmission, User
from app.utils.time import utc_now


PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
PNG_BYTES_2 = b"\x89PNG\r\n\x1a\nsecond-image"
JPEG_BYTES = b"\xff\xd8\xff\xe0jpeg-body"
WEBP_BYTES = b"RIFF\x10\x00\x00\x00WEBPVP8 "
GIF_BYTES = b"GIF89a"
SVG_BYTES = b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"


@pytest.fixture()
def image_db(app, tmp_path):
    upload_root = tmp_path / "task-images"
    app.config["TASK_IMAGE_UPLOAD_DIR"] = str(upload_root)
    app.config["TASK_IMAGE_MAX_BYTES"] = 64
    with app.app_context():
        db.create_all()
        yield upload_root
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


def create_child(child_id, user_id):
    child = Child(
        id=child_id,
        user_id=user_id,
        name="小小探索家",
        age=7,
        age_group="7-12",
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


def setup_task(app, *, plan_status="in-progress"):
    with app.app_context():
        create_user(1, "13800138000")
        create_user(2, "13800138001")
        create_child(10, 1)
        create_child(20, 2)
        create_plan(100, 1, 10, status=plan_status)
        create_plan(200, 2, 20)
        create_task(1000, 100)
        create_task(2000, 200)
    return auth_headers(app, 1)


def image_path(plan_id=100, task_id=1000):
    return f"/api/v1/plans/{plan_id}/tasks/{task_id}/submission/image"


def multipart_image(content, filename="photo.jpg"):
    return {"image": (BytesIO(content), filename)}


def post_image(client, headers, content=PNG_BYTES, filename="photo.jpg", plan_id=100, task_id=1000):
    return client.post(
        image_path(plan_id, task_id),
        data=multipart_image(content, filename),
        headers=headers,
        content_type="multipart/form-data",
    )


def assert_error(response, status, code):
    assert response.status_code == status
    assert response.get_json()["error"]["code"] == code


def stored_file(upload_root, storage_key):
    return upload_root / storage_key.removeprefix("task-images/")


def test_upload_requires_token(client):
    response = client.post(image_path(), data=multipart_image(PNG_BYTES), content_type="multipart/form-data")

    assert_error(response, 401, "UNAUTHORIZED")


def test_upload_plan_and_task_ownership_errors(client, app, image_db):
    headers = setup_task(app)

    assert_error(post_image(client, headers, plan_id=999), 404, "PLAN_NOT_FOUND")
    assert_error(post_image(client, auth_headers(app, 2)), 404, "PLAN_NOT_FOUND")
    assert_error(post_image(client, headers, task_id=999), 404, "TASK_NOT_FOUND")
    assert_error(post_image(client, headers, task_id=2000), 404, "TASK_NOT_FOUND")


@pytest.mark.parametrize(
    ("plan_status", "code"),
    [
        ("draft", "PLAN_NOT_READY"),
        ("ready", "PLAN_NOT_STARTED"),
    ],
)
def test_upload_rejects_plan_statuses_that_are_not_in_progress(client, app, image_db, plan_status, code):
    headers = setup_task(app, plan_status=plan_status)

    response = post_image(client, headers)

    assert_error(response, 409, code)


def test_upload_requires_non_empty_image_file(client, app, image_db):
    headers = setup_task(app)

    missing = client.post(image_path(), data={}, headers=headers, content_type="multipart/form-data")
    empty = post_image(client, headers, b"", "empty.png")

    assert_error(missing, 400, "IMAGE_REQUIRED")
    assert_error(empty, 400, "IMAGE_REQUIRED")
    with app.app_context():
        assert TaskSubmission.query.count() == 0


@pytest.mark.parametrize("content", [b"plain text", SVG_BYTES, GIF_BYTES])
def test_upload_rejects_unsupported_file_types_without_creating_submission(client, app, image_db, content):
    headers = setup_task(app)

    response = post_image(client, headers, content, "fake.png")

    assert_error(response, 400, "UNSUPPORTED_IMAGE_TYPE")
    with app.app_context():
        assert TaskSubmission.query.count() == 0


def test_upload_rejects_files_over_configured_size(client, app, image_db):
    app.config["TASK_IMAGE_MAX_BYTES"] = len(PNG_BYTES) - 1
    headers = setup_task(app)

    response = post_image(client, headers, PNG_BYTES)

    assert_error(response, 413, "IMAGE_TOO_LARGE")
    with app.app_context():
        assert TaskSubmission.query.count() == 0


@pytest.mark.parametrize(
    ("content", "filename", "suffix"),
    [
        (PNG_BYTES, "../../原始.jpg", ".png"),
        (JPEG_BYTES, "fake.png", ".jpg"),
        (WEBP_BYTES, "fake.gif", ".webp"),
    ],
)
def test_upload_detects_real_type_and_stores_safe_internal_key(client, app, image_db, content, filename, suffix):
    headers = setup_task(app)

    response = post_image(client, headers, content, filename)

    assert response.status_code == 200
    task = response.get_json()["data"]["task"]
    assert task["status"] == "in-progress"
    assert task["record"]["imageUrl"] == "/api/v1/plans/100/tasks/1000/submission/image"
    with app.app_context():
        submission = TaskSubmission.query.filter_by(task_id=1000).one()
        assert re.fullmatch(r"task-images/[0-9a-f]{32}" + re.escape(suffix), submission.image_url)
        assert filename not in submission.image_url
        assert not os.path.isabs(submission.image_url)
        assert ":" not in submission.image_url
        assert stored_file(image_db, submission.image_url).read_bytes() == content


def test_upload_preserves_note_and_completed_state_while_replacing_image(client, app, image_db):
    headers = setup_task(app)
    completed_at = utc_now() - timedelta(minutes=5)
    with app.app_context():
        db.session.add(
            TaskSubmission(
                id=5000,
                task_id=1000,
                status="completed",
                image_url=None,
                note="已经完成的记录",
                completed_at=completed_at,
            )
        )
        db.session.commit()

    first = post_image(client, headers, PNG_BYTES)
    assert first.status_code == 200
    with app.app_context():
        submission = TaskSubmission.query.filter_by(task_id=1000).one()
        first_key = submission.image_url
        first_id = submission.id
        first_file = stored_file(image_db, first_key)
        assert first_file.exists()

    second = post_image(client, headers, PNG_BYTES_2)

    assert second.status_code == 200
    task = second.get_json()["data"]["task"]
    assert task["status"] == "completed"
    assert task["record"]["note"] == "已经完成的记录"
    assert task["completedAt"] == f"{completed_at.isoformat()}Z"
    with app.app_context():
        submission = TaskSubmission.query.filter_by(task_id=1000).one()
        assert submission.id == first_id
        assert submission.image_url != first_key
        assert submission.status == "completed"
        assert submission.completed_at == completed_at
        assert not first_file.exists()
        assert stored_file(image_db, submission.image_url).read_bytes() == PNG_BYTES_2


@pytest.mark.parametrize("record_status", [None, "draft"])
def test_upload_allows_completed_plan_completed_submission_with_missing_or_draft_record(
    client, app, image_db, record_status
):
    headers = setup_task(app, plan_status="completed")
    completed_at = utc_now() - timedelta(minutes=5)
    with app.app_context():
        db.session.add(
            TaskSubmission(
                id=5000,
                task_id=1000,
                status="completed",
                image_url=None,
                note="old note",
                completed_at=completed_at,
            )
        )
        if record_status is not None:
            db.session.add(JourneyRecord(id=6000, plan_id=100, status=record_status))
        db.session.commit()

    first = post_image(client, headers, PNG_BYTES)
    assert first.status_code == 200
    with app.app_context():
        submission = TaskSubmission.query.filter_by(task_id=1000).one()
        first_key = submission.image_url
        first_file = stored_file(image_db, first_key)
        assert first_file.exists()

    second = post_image(client, headers, PNG_BYTES_2)

    assert second.status_code == 200
    with app.app_context():
        submission = TaskSubmission.query.filter_by(task_id=1000).one()
        assert submission.id == 5000
        assert submission.status == "completed"
        assert submission.note == "old note"
        assert submission.completed_at == completed_at
        assert submission.image_url != first_key
        assert not first_file.exists()
        assert stored_file(image_db, submission.image_url).read_bytes() == PNG_BYTES_2


def test_upload_rejects_completed_plan_finalized_record_before_writing_file(client, app, image_db):
    headers = setup_task(app, plan_status="completed")
    completed_at = utc_now() - timedelta(minutes=5)
    with app.app_context():
        db.session.add(
            TaskSubmission(
                id=5000,
                task_id=1000,
                status="completed",
                image_url=None,
                note="old note",
                completed_at=completed_at,
            )
        )
        db.session.add(JourneyRecord(id=6000, plan_id=100, status="finalized"))
        db.session.commit()
        before_submission = TaskSubmission.query.filter_by(task_id=1000).one()
        before = (before_submission.status, before_submission.image_url, before_submission.note, before_submission.completed_at)

    response = post_image(client, headers, PNG_BYTES)

    assert_error(response, 409, "JOURNEY_RECORD_FINALIZED")
    assert not image_db.exists()
    with app.app_context():
        submission = TaskSubmission.query.filter_by(task_id=1000).one()
        assert (submission.status, submission.image_url, submission.note, submission.completed_at) == before


@pytest.mark.parametrize("submission_status", [None, "in-progress"])
def test_upload_rejects_completed_plan_without_completed_submission(client, app, image_db, submission_status):
    headers = setup_task(app, plan_status="completed")
    with app.app_context():
        if submission_status is not None:
            db.session.add(TaskSubmission(id=5000, task_id=1000, status=submission_status, image_url=None, note="old note"))
            db.session.commit()

    response = post_image(client, headers, PNG_BYTES)

    assert_error(response, 409, "TASK_CORRECTION_REQUIRES_COMPLETED_SUBMISSION")
    assert not image_db.exists()
    with app.app_context():
        submission = TaskSubmission.query.filter_by(task_id=1000).one_or_none()
        if submission_status is None:
            assert submission is None
        else:
            assert submission.status == "in-progress"
            assert submission.image_url is None


def test_db_failure_removes_new_file_and_keeps_old_image(client, app, image_db, monkeypatch):
    headers = setup_task(app)
    assert post_image(client, headers, PNG_BYTES).status_code == 200
    with app.app_context():
        old_key = TaskSubmission.query.filter_by(task_id=1000).one().image_url
        old_file = stored_file(image_db, old_key)

    def fail_commit():
        raise RuntimeError("commit failed")

    monkeypatch.setattr(db.session, "commit", fail_commit)

    response = post_image(client, headers, PNG_BYTES_2)

    assert_error(response, 500, "DATABASE_ERROR")
    with app.app_context():
        db.session.rollback()
        submission = TaskSubmission.query.filter_by(task_id=1000).one()
        assert submission.image_url == old_key
        assert old_file.exists()
        assert sorted(image_db.iterdir()) == [old_file]


def test_get_image_requires_token_and_enforces_ownership(client, app, image_db):
    headers = setup_task(app)
    assert post_image(client, headers, PNG_BYTES).status_code == 200

    no_token = client.get(image_path())
    other_user = client.get(image_path(), headers=auth_headers(app, 2))

    assert_error(no_token, 401, "UNAUTHORIZED")
    assert_error(other_user, 404, "PLAN_NOT_FOUND")


def test_get_image_returns_bytes_content_type_and_private_cache(client, app, image_db):
    headers = setup_task(app)
    assert post_image(client, headers, WEBP_BYTES, "photo.jpg").status_code == 200

    response = client.get(image_path(), headers=headers)

    assert response.status_code == 200
    assert response.data == WEBP_BYTES
    assert response.headers["Content-Type"].startswith("image/webp")
    assert response.headers["Content-Disposition"].startswith("inline")
    assert response.headers["Cache-Control"] == "private"


def test_get_image_returns_not_found_for_missing_submission_file_or_unsafe_key(client, app, image_db):
    headers = setup_task(app)

    assert_error(client.get(image_path(), headers=headers), 404, "TASK_IMAGE_NOT_FOUND")
    with app.app_context():
        db.session.add(TaskSubmission(id=5000, task_id=1000, status="in-progress", image_url="task-images/missing.png"))
        db.session.commit()
    assert_error(client.get(image_path(), headers=headers), 404, "TASK_IMAGE_NOT_FOUND")
    with app.app_context():
        submission = TaskSubmission.query.filter_by(task_id=1000).one()
        submission.image_url = "../escape.png"
        db.session.commit()
    assert_error(client.get(image_path(), headers=headers), 404, "TASK_IMAGE_NOT_FOUND")


def test_list_and_detail_return_authenticated_image_url_without_storage_path(client, app, image_db):
    headers = setup_task(app)
    assert post_image(client, headers, PNG_BYTES).status_code == 200

    list_response = client.get("/api/v1/plans/100/tasks", headers=headers)
    detail_response = client.get("/api/v1/plans/100/tasks/1000", headers=headers)

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    list_url = list_response.get_json()["data"]["tasks"][0]["record"]["imageUrl"]
    detail_url = detail_response.get_json()["data"]["task"]["record"]["imageUrl"]
    assert list_url == "/api/v1/plans/100/tasks/1000/submission/image"
    assert detail_url == list_url
    assert "task-images/" not in list_url
    assert ":" not in list_url
