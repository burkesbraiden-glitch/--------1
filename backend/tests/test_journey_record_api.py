import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Child, ExplorationPlan, JourneyRecord, Task, TaskSubmission, User
from app.utils.time import utc_now


@pytest.fixture()
def journey_api_db(app):
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
    db.session.add(User(id=user_id, phone=phone, nickname=f"user-{user_id}"))
    db.session.commit()


def create_child(child_id, user_id):
    db.session.add(
        Child(
            id=child_id,
            user_id=user_id,
            name=f"child-{child_id}",
            age=7,
            age_group="7-12",
            interests=[],
            is_default=True,
        )
    )
    db.session.commit()


def create_plan(plan_id, user_id, child_id, *, status="ready"):
    db.session.add(
        ExplorationPlan(
            id=plan_id,
            user_id=user_id,
            child_id=child_id,
            title=f"plan-{plan_id}",
            destination="museum",
            age_group="7-12",
            duration="3h",
            interests=[],
            status=status,
        )
    )
    db.session.commit()


def create_record(record_id, plan_id, *, status="draft", custom_title=None):
    db.session.add(
        JourneyRecord(
            id=record_id,
            plan_id=plan_id,
            status=status,
            custom_title=custom_title,
            finalized_at=utc_now() if status == "finalized" else None,
        )
    )
    db.session.commit()


def create_task_and_submission(plan_id, task_id, submission_id, *, image_url=None, note="note"):
    db.session.add(
        Task(
            id=task_id,
            plan_id=plan_id,
            sort_order=1,
            title="observe",
            subtitle="subtitle",
            age_group="7-12",
            duration="20m",
            task_type="observe",
            summary="summary",
            objective="objective",
            steps=[],
            questions=[],
            record_mode="note",
            theme=None,
        )
    )
    db.session.add(
        TaskSubmission(
            id=submission_id,
            task_id=task_id,
            status="completed",
            image_url=image_url,
            note=note,
            completed_at=utc_now(),
        )
    )
    db.session.commit()


def seed(app, *, own_record=True, own_status="ready"):
    with app.app_context():
        create_user(1, "13800000001")
        create_user(2, "13800000002")
        create_child(10, 1)
        create_child(20, 2)
        create_plan(100, 1, 10, status=own_status)
        create_plan(101, 1, 10, status="in-progress")
        create_plan(200, 2, 20, status="ready")
        if own_record:
            create_record(1000, 100)
        create_record(2000, 200)
    return auth_headers(app, 1), auth_headers(app, 2)


def assert_error(response, status, code):
    assert response.status_code == status
    payload = response.get_json()
    assert payload["success"] is False
    assert set(payload["error"]) == {"code", "message", "details"}
    assert payload["error"]["code"] == code
    assert isinstance(payload["error"]["message"], str)
    assert isinstance(payload["error"]["details"], dict)


def record_path(plan_id=100, suffix=""):
    return f"/api/v1/plans/{plan_id}/journey-record{suffix}"


def journey_record_state(plan_id=100):
    record = JourneyRecord.query.filter_by(plan_id=plan_id).first()
    return (
        JourneyRecord.query.count(),
        None
        if record is None
        else (
            record.id,
            record.status,
            record.custom_title,
            record.summary,
            record.cover_submission_id,
            record.finalized_at,
            record.updated_at,
        ),
    )


def non_journey_state(plan_id=100):
    plan = db.session.get(ExplorationPlan, plan_id)
    tasks = Task.query.filter_by(plan_id=plan_id).order_by(Task.id).all()
    submissions = (
        TaskSubmission.query.join(Task)
        .filter(Task.plan_id == plan_id)
        .order_by(TaskSubmission.id)
        .all()
    )
    return {
        "plan": (plan.id, plan.title, plan.status, plan.updated_at),
        "tasks": [
            (task.id, getattr(task, "status", None), task.sort_order, task.title)
            for task in tasks
        ],
        "submissions": [
            (
                submission.id,
                submission.status,
                submission.note,
                submission.image_url,
                submission.completed_at,
            )
            for submission in submissions
        ],
    }


def assert_public_response_shape(value):
    forbidden = {
        "custom_title",
        "cover_submission_id",
        "finalized_at",
        "created_at",
        "updated_at",
        "image_url",
        "image_path",
        "storage_key",
        "_storage_key",
        "_sa_instance_state",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            assert "_" not in key
            assert key not in forbidden
            assert_public_response_shape(child)
    elif isinstance(value, list):
        for child in value:
            assert_public_response_shape(child)
    else:
        assert value is None or isinstance(value, (bool, int, float, str))


def test_all_journey_record_routes_require_jwt(client):
    requests = (
        lambda: client.get("/api/v1/journey-records"),
        lambda: client.get(record_path()),
        lambda: client.post(record_path()),
        lambda: client.patch(record_path(), json={"summary": "x"}),
        lambda: client.post(record_path(suffix="/finalize")),
    )

    for request in requests:
        assert_error(request(), 401, "UNAUTHORIZED")


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    (
        ("GET", "/api/v1/journey-records", {}),
        ("GET", record_path(), {}),
        ("POST", record_path(), {}),
        ("PATCH", record_path(), {"json": {"summary": "ignored"}}),
        ("POST", record_path(suffix="/finalize"), {}),
    ),
)
def test_all_journey_record_routes_reject_invalid_jwt(client, app, journey_api_db, method, path, kwargs):
    seed(app)
    with app.app_context():
        create_task_and_submission(100, 501, 5501, image_url="private/one.jpg")
        before_record = journey_record_state()
        before_non_journey = non_journey_state()

    response = client.open(
        path,
        method=method,
        headers={"Authorization": "Bearer invalid-token"},
        **kwargs,
    )

    assert_error(response, 401, "INVALID_TOKEN")
    with app.app_context():
        assert journey_record_state() == before_record
        assert non_journey_state() == before_non_journey


def test_list_returns_only_owned_records_with_default_pagination_and_no_entries(client, app, journey_api_db):
    headers, _ = seed(app)
    with app.app_context():
        create_record(1001, 101, status="finalized")
        create_task_and_submission(100, 501, 5501, image_url="private/one.jpg")

    response = client.get("/api/v1/journey-records", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True and payload["message"] == "ok"
    assert payload["data"]["total"] == 2
    assert payload["data"]["limit"] == 20 and payload["data"]["offset"] == 0
    assert {item["planId"] for item in payload["data"]["items"]} == {100, 101}
    assert all("entries" not in item for item in payload["data"]["items"])
    assert "private/one.jpg" not in str(payload)


def test_list_supports_child_status_and_page_filters(client, app, journey_api_db):
    headers, _ = seed(app)
    with app.app_context():
        create_record(1001, 101, status="finalized")

    response = client.get(
        "/api/v1/journey-records?childId=10&status=finalized&limit=1&offset=0",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["total"] == 1 and data["limit"] == 1 and data["offset"] == 0
    assert [item["id"] for item in data["items"]] == [1001]


def test_list_applies_offset_without_changing_total(client, app, journey_api_db):
    headers, _ = seed(app)
    with app.app_context():
        create_record(1001, 101, status="finalized")

    response = client.get("/api/v1/journey-records?limit=1&offset=1", headers=headers)

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["total"] == 2 and len(data["items"]) == 1 and data["offset"] == 1


@pytest.mark.parametrize(
    "query",
    (
        "childId=",
        "childId=0",
        "childId=-1",
        "childId=abc",
        "childId=1.5",
        "childId=true",
        "childId=false",
        "childId=1abc",
        "childId=%20",
        "childId=%2B1",
        "limit=",
        "limit=0",
        "limit=-1",
        "limit=101",
        "limit=abc",
        "limit=1.5",
        "limit=true",
        "limit=%20",
        "offset=",
        "offset=-1",
        "offset=abc",
        "offset=1.5",
        "offset=true",
        "offset=%20",
        "status=",
        "status=Draft",
        "status=FINALIZED",
        "status=completed",
        "status=true",
        "status=%20",
    ),
)
def test_list_rejects_invalid_query_parameters(client, app, journey_api_db, query):
    headers, _ = seed(app)
    with app.app_context():
        create_task_and_submission(100, 501, 5501, image_url="private/one.jpg")
        before_record = journey_record_state()
        before_non_journey = non_journey_state()

    response = client.get(f"/api/v1/journey-records?{query}", headers=headers)

    assert_error(response, 400, "VALIDATION_ERROR")
    assert "data" not in response.get_json()
    with app.app_context():
        assert journey_record_state() == before_record
        assert non_journey_state() == before_non_journey


def test_list_hides_other_users_child(client, app, journey_api_db):
    headers, _ = seed(app)

    assert_error(client.get("/api/v1/journey-records?childId=20", headers=headers), 404, "CHILD_NOT_FOUND")


def test_detail_returns_full_record_without_creating_missing_data(client, app, journey_api_db):
    headers, _ = seed(app)
    with app.app_context():
        create_task_and_submission(100, 501, 5501, image_url="private/one.jpg")
        before = JourneyRecord.query.count()
        updated_at = db.session.get(JourneyRecord, 1000).updated_at

    response = client.get(record_path(), headers=headers)

    assert response.status_code == 200
    record = response.get_json()["data"]["journeyRecord"]
    assert record["planId"] == 100 and record["entries"][0]["taskId"] == 501
    assert record["entries"][0]["imageUrl"].endswith("/plans/100/tasks/501/submission/image")
    assert "private/one.jpg" not in str(record)
    with app.app_context():
        assert JourneyRecord.query.count() == before
        assert db.session.get(JourneyRecord, 1000).updated_at == updated_at


def test_detail_and_list_audit_public_response_fields_and_cover_isolation(client, app, journey_api_db):
    headers, _ = seed(app)
    with app.app_context():
        create_task_and_submission(100, 501, 5501, image_url="private/one.jpg")
        create_task_and_submission(101, 502, 5502, image_url="private/other.jpg")
        record = db.session.get(JourneyRecord, 1000)
        record.cover_submission_id = 5501
        db.session.commit()

    detail_response = client.get(record_path(), headers=headers)

    assert detail_response.status_code == 200
    detail_payload = detail_response.get_json()
    assert_public_response_shape(detail_payload)
    detail = detail_payload["data"]["journeyRecord"]
    assert "entries" in detail
    assert detail["coverImageUrl"].endswith("/plans/100/tasks/501/submission/image")
    assert detail["entries"][0]["imageUrl"].endswith("/plans/100/tasks/501/submission/image")
    assert "private/" not in str(detail_payload)

    list_response = client.get("/api/v1/journey-records", headers=headers)

    assert list_response.status_code == 200
    list_payload = list_response.get_json()
    assert_public_response_shape(list_payload)
    assert all("entries" not in item for item in list_payload["data"]["items"])

    with app.app_context():
        record = db.session.get(JourneyRecord, 1000)
        record.cover_submission_id = 5502
        db.session.commit()
        db.session.expire_all()

    isolated_cover_response = client.get(record_path(), headers=headers)

    assert isolated_cover_response.status_code == 200
    assert isolated_cover_response.get_json()["data"]["journeyRecord"]["coverImageUrl"] is None


def test_detail_hides_missing_other_user_and_missing_record(client, app, journey_api_db):
    headers, _ = seed(app)

    assert_error(client.get(record_path(200), headers=headers), 404, "PLAN_NOT_FOUND")
    assert_error(client.get(record_path(101), headers=headers), 404, "JOURNEY_RECORD_NOT_FOUND")


def test_create_allows_empty_body_is_idempotent_and_returns_full_record(client, app, journey_api_db):
    headers, _ = seed(app, own_record=False)
    with app.app_context():
        create_task_and_submission(100, 501, 5501, image_url="private/one.jpg")
        plan = db.session.get(ExplorationPlan, 100)
        submission = db.session.get(TaskSubmission, 5501)
        plan_snapshot = (plan.title, plan.status)
        submission_snapshot = (submission.status, submission.image_url, submission.note, submission.completed_at)

    first = client.post(record_path(), headers=headers)
    first_updated_at = first.get_json()["data"]["journeyRecord"]["updatedAt"]
    second = client.post(record_path(), json={}, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 200
    first_data, second_data = first.get_json()["data"], second.get_json()["data"]
    assert first_data["created"] is True and second_data["created"] is False
    assert first_data["journeyRecord"]["id"] == second_data["journeyRecord"]["id"]
    assert second_data["journeyRecord"]["updatedAt"] == first_updated_at
    assert "entries" in first_data["journeyRecord"]
    with app.app_context():
        assert JourneyRecord.query.filter_by(plan_id=100).count() == 1
        plan = db.session.get(ExplorationPlan, 100)
        submission = db.session.get(TaskSubmission, 5501)
        assert (plan.title, plan.status) == plan_snapshot
        assert (submission.status, submission.image_url, submission.note, submission.completed_at) == submission_snapshot


@pytest.mark.parametrize("payload", ({"summary": "not allowed"}, [], "x", 1))
def test_create_rejects_nonempty_or_nonobject_body(client, app, journey_api_db, payload):
    headers, _ = seed(app, own_record=False)

    assert_error(client.post(record_path(), json=payload, headers=headers), 400, "VALIDATION_ERROR")


def test_create_rejects_non_json_nonempty_body(client, app, journey_api_db):
    headers, _ = seed(app, own_record=False)

    response = client.post(record_path(), data="unexpected", content_type="text/plain", headers=headers)

    assert_error(response, 400, "VALIDATION_ERROR")


@pytest.mark.parametrize(
    ("body", "content_type"),
    (
        ("null", "application/json"),
        ("true", "application/json"),
        ("false", "application/json"),
        ("{", "application/json"),
        ("abc", "text/plain"),
        ("[]", "application/json"),
        ('""', "application/json"),
        ("0", "application/json"),
    ),
)
def test_create_rejects_raw_invalid_bodies_without_writes(client, app, journey_api_db, body, content_type):
    headers, _ = seed(app, own_record=False)
    with app.app_context():
        create_task_and_submission(100, 501, 5501, image_url="private/one.jpg")
        before_record = journey_record_state()
        before_non_journey = non_journey_state()

    response = client.post(record_path(), data=body, content_type=content_type, headers=headers)

    assert_error(response, 400, "VALIDATION_ERROR")
    with app.app_context():
        assert journey_record_state() == before_record
        assert non_journey_state() == before_non_journey


def test_create_respects_plan_status_and_ownership(client, app, journey_api_db):
    draft_headers, _ = seed(app, own_record=False, own_status="draft")

    assert_error(client.post(record_path(), headers=draft_headers), 409, "PLAN_NOT_READY")
    assert_error(client.post(record_path(200), headers=draft_headers), 404, "PLAN_NOT_FOUND")


def test_patch_updates_and_clears_only_journey_record_fields(client, app, journey_api_db):
    headers, _ = seed(app)
    with app.app_context():
        create_task_and_submission(100, 501, 5501, image_url="private/cover.jpg")
        before_non_journey = non_journey_state()

    response = client.patch(
        record_path(),
        json={"customTitle": "  My journey  ", "summary": "  First line\n  Second line  ", "coverSubmissionId": 5501},
        headers=headers,
    )

    assert response.status_code == 200
    record = response.get_json()["data"]["journeyRecord"]
    assert record["customTitle"] == "My journey" and record["summary"] == "First line\n  Second line"
    assert record["coverSubmissionId"] == 5501
    assert record["coverImageUrl"].endswith("/plans/100/tasks/501/submission/image")
    with app.app_context():
        assert non_journey_state() == before_non_journey
    clear = client.patch(record_path(), json={"customTitle": None, "summary": "   ", "coverSubmissionId": None}, headers=headers)
    cleared_record = clear.get_json()["data"]["journeyRecord"]
    assert cleared_record["customTitle"] is None and cleared_record["summary"] is None
    assert cleared_record["coverSubmissionId"] is None and cleared_record["coverImageUrl"] is None
    with app.app_context():
        assert non_journey_state() == before_non_journey


@pytest.mark.parametrize(
    "payload",
    ({}, None, [], "x", {"unknown": "x"}, {"custom_title": "x"}, {"status": "finalized"}, {"finalizedAt": "x"}, {"customTitle": 1}, {"summary": "x" * 2001}, {"customTitle": "x" * 121}, {"coverSubmissionId": True}),
)
def test_patch_rejects_invalid_contract_payloads(client, app, journey_api_db, payload):
    headers, _ = seed(app)

    if payload is None:
        response = client.patch(record_path(), headers=headers)
    else:
        response = client.patch(record_path(), json=payload, headers=headers)
    assert_error(response, 400, "VALIDATION_ERROR")


@pytest.mark.parametrize(
    ("body", "content_type"),
    (
        ("null", "application/json"),
        ("true", "application/json"),
        ("false", "application/json"),
        ("0", "application/json"),
        ('"text"', "application/json"),
        ("[]", "application/json"),
        ("{", "application/json"),
        ("abc", "text/plain"),
    ),
)
def test_patch_rejects_raw_nonobject_bodies_without_writes(client, app, journey_api_db, body, content_type):
    headers, _ = seed(app)
    with app.app_context():
        create_task_and_submission(100, 501, 5501, image_url="private/one.jpg")
        record = db.session.get(JourneyRecord, 1000)
        record.custom_title = "Before title"
        record.summary = "Before summary"
        record.cover_submission_id = 5501
        db.session.commit()
        before_record = journey_record_state()
        before_non_journey = non_journey_state()

    response = client.patch(record_path(), data=body, content_type=content_type, headers=headers)

    assert_error(response, 400, "VALIDATION_ERROR")
    with app.app_context():
        assert journey_record_state() == before_record
        assert non_journey_state() == before_non_journey


def test_patch_rejects_cover_from_other_plan_or_without_image(client, app, journey_api_db):
    headers, _ = seed(app)
    with app.app_context():
        create_task_and_submission(101, 502, 5502, image_url="private/other.jpg")
        db.session.add(
            Task(
                id=503, plan_id=100, sort_order=1, title="no image", subtitle="", age_group="7-12",
                duration="20m", task_type="observe", summary="", objective="objective", steps=[], questions=[], record_mode="note", theme=None,
            )
        )
        db.session.add(TaskSubmission(id=5503, task_id=503, status="completed", image_url=None, note="", completed_at=utc_now()))
        create_task_and_submission(200, 504, 5504, image_url="private/other-user.jpg")
        db.session.commit()
        before_non_journey = non_journey_state()

    assert_error(client.patch(record_path(), json={"coverSubmissionId": 5502}, headers=headers), 400, "INVALID_COVER_SUBMISSION")
    assert_error(client.patch(record_path(), json={"coverSubmissionId": 5503}, headers=headers), 400, "INVALID_COVER_SUBMISSION")
    assert_error(client.patch(record_path(), json={"coverSubmissionId": 5504}, headers=headers), 400, "INVALID_COVER_SUBMISSION")
    assert_error(client.patch(record_path(), json={"coverSubmissionId": 0}, headers=headers), 400, "INVALID_COVER_SUBMISSION")
    with app.app_context():
        assert non_journey_state() == before_non_journey


def test_patch_rejects_finalized_record_without_mutating_plan(client, app, journey_api_db):
    headers, _ = seed(app)
    with app.app_context():
        create_task_and_submission(100, 501, 5501, image_url="private/one.jpg")
        record = db.session.get(JourneyRecord, 1000)
        record.status, record.finalized_at = "finalized", utc_now()
        db.session.commit()
        before_non_journey = non_journey_state()

    assert_error(client.patch(record_path(), json={"summary": "cannot edit"}, headers=headers), 409, "JOURNEY_RECORD_FINALIZED")
    with app.app_context():
        assert non_journey_state() == before_non_journey


def test_patch_noop_and_missing_or_other_user_record_do_not_write(client, app, journey_api_db):
    headers, _ = seed(app)
    with app.app_context():
        record = db.session.get(JourneyRecord, 1000)
        record.summary = "unchanged"
        db.session.commit()
        updated_at = record.updated_at

    response = client.patch(record_path(), json={"summary": "unchanged"}, headers=headers)

    assert response.status_code == 200
    assert response.get_json()["data"]["journeyRecord"]["updatedAt"] == f"{updated_at.isoformat()}Z"
    assert_error(client.patch(record_path(101), json={"summary": "x"}, headers=headers), 404, "JOURNEY_RECORD_NOT_FOUND")
    assert_error(client.patch(record_path(200), json={"summary": "x"}, headers=headers), 404, "PLAN_NOT_FOUND")


def test_finalize_is_idempotent_and_does_not_change_plan_or_submission(client, app, journey_api_db):
    headers, _ = seed(app)
    with app.app_context():
        create_task_and_submission(100, 501, 5501, image_url="private/one.jpg")
        plan = db.session.get(ExplorationPlan, 100)
        submission = db.session.get(TaskSubmission, 5501)
        plan_snapshot = (plan.title, plan.status)
        submission_snapshot = (submission.status, submission.image_url, submission.note, submission.completed_at)

    first = client.post(record_path(suffix="/finalize"), headers=headers)
    second = client.post(record_path(suffix="/finalize"), json={}, headers=headers)

    assert first.status_code == second.status_code == 200
    assert first.get_json()["data"]["finalizedNow"] is True
    assert second.get_json()["data"]["finalizedNow"] is False
    assert first.get_json()["data"]["journeyRecord"]["status"] == "finalized"
    assert first.get_json()["data"]["journeyRecord"]["finalizedAt"] == second.get_json()["data"]["journeyRecord"]["finalizedAt"]
    assert first.get_json()["data"]["journeyRecord"]["updatedAt"] == second.get_json()["data"]["journeyRecord"]["updatedAt"]
    with app.app_context():
        plan = db.session.get(ExplorationPlan, 100)
        submission = db.session.get(TaskSubmission, 5501)
        assert (plan.title, plan.status) == plan_snapshot
        assert (submission.status, submission.image_url, submission.note, submission.completed_at) == submission_snapshot


@pytest.mark.parametrize("payload", ({"status": "finalized"}, [], "x", 1))
def test_finalize_rejects_nonempty_or_nonobject_body(client, app, journey_api_db, payload):
    headers, _ = seed(app)

    assert_error(client.post(record_path(suffix="/finalize"), json=payload, headers=headers), 400, "VALIDATION_ERROR")


def test_finalize_rejects_non_json_nonempty_body(client, app, journey_api_db):
    headers, _ = seed(app)

    response = client.post(record_path(suffix="/finalize"), data="unexpected", content_type="text/plain", headers=headers)

    assert_error(response, 400, "VALIDATION_ERROR")


@pytest.mark.parametrize(
    ("body", "content_type"),
    (
        ("null", "application/json"),
        ("true", "application/json"),
        ("false", "application/json"),
        ("{", "application/json"),
        ("abc", "text/plain"),
        ("[]", "application/json"),
        ('""', "application/json"),
        ("0", "application/json"),
    ),
)
def test_finalize_rejects_raw_invalid_bodies_without_writes(client, app, journey_api_db, body, content_type):
    headers, _ = seed(app)
    with app.app_context():
        create_task_and_submission(100, 501, 5501, image_url="private/one.jpg")
        before_record = journey_record_state()
        before_non_journey = non_journey_state()

    response = client.post(record_path(suffix="/finalize"), data=body, content_type=content_type, headers=headers)

    assert_error(response, 400, "VALIDATION_ERROR")
    with app.app_context():
        assert journey_record_state() == before_record
        assert non_journey_state() == before_non_journey


def test_finalize_hides_missing_record_and_other_users_plan(client, app, journey_api_db):
    headers, _ = seed(app)

    assert_error(client.post(record_path(101, "/finalize"), headers=headers), 404, "JOURNEY_RECORD_NOT_FOUND")
    assert_error(client.post(record_path(200, "/finalize"), headers=headers), 404, "PLAN_NOT_FOUND")


@pytest.mark.parametrize(
    ("scenario", "status", "code"),
    (
        ("validation", 400, "VALIDATION_ERROR"),
        ("invalid_cover", 400, "INVALID_COVER_SUBMISSION"),
        ("missing_record", 404, "JOURNEY_RECORD_NOT_FOUND"),
        ("plan_not_ready", 409, "PLAN_NOT_READY"),
        ("finalized", 409, "JOURNEY_RECORD_FINALIZED"),
        ("invalid_token", 401, "INVALID_TOKEN"),
    ),
)
def test_journey_record_errors_have_safe_consistent_envelopes(client, app, journey_api_db, scenario, status, code):
    headers, _ = seed(app, own_record=scenario != "plan_not_ready", own_status="draft" if scenario == "plan_not_ready" else "ready")
    if scenario == "validation":
        response = client.patch(record_path(), data="null", content_type="application/json", headers=headers)
    elif scenario == "invalid_cover":
        with app.app_context():
            create_task_and_submission(101, 502, 5502, image_url="private/other.jpg")
        response = client.patch(record_path(), json={"coverSubmissionId": 5502}, headers=headers)
    elif scenario == "missing_record":
        response = client.get(record_path(101), headers=headers)
    elif scenario == "plan_not_ready":
        response = client.post(record_path(), headers=headers)
    elif scenario == "finalized":
        with app.app_context():
            record = db.session.get(JourneyRecord, 1000)
            record.status, record.finalized_at = "finalized", utc_now()
            db.session.commit()
        response = client.patch(record_path(), json={"summary": "blocked"}, headers=headers)
    else:
        response = client.get("/api/v1/journey-records", headers={"Authorization": "Bearer invalid-token"})

    assert_error(response, status, code)
    payload_text = str(response.get_json())
    assert not any(value in payload_text for value in ("Traceback", "SELECT ", "FROM ", "D:\\", "private/"))
    assert response.status_code != 500


def record_image_snapshot(record_id, asset):
    return {
        "schemaVersion": 1,
        "record": {
            "id": record_id, "planId": 100, "childId": 10, "title": "plan-100",
            "customTitle": None, "displayTitle": "plan-100", "destination": "museum",
            "planStatus": "completed", "status": "finalized", "summary": None,
            "coverSubmissionId": None, "taskCount": 0, "completedTaskCount": 0,
            "photoCount": 1, "noteCount": 0, "finalizedAt": "2026-08-06T00:00:00Z",
            "createdAt": "2026-08-06T00:00:00Z", "updatedAt": "2026-08-06T00:00:00Z",
        },
        "cover": {"submissionId": None, "imageAssetId": None},
        "entries": [],
        "imageAssets": [asset],
    }


def test_record_image_download_requires_owner_finalized_snapshot_and_private_cache(client, app, journey_api_db, tmp_path):
    headers, _ = seed(app)
    root = tmp_path / "record-images"
    target = root / "1000" / "asset.png"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    app.config["RECORD_IMAGE_UPLOAD_DIR"] = str(root)
    with app.app_context():
        record = db.session.get(JourneyRecord, 1000)
        record.status = "finalized"
        record.snapshot = record_image_snapshot(1000, {
            "id": "img-01", "storageKey": "record-images/1000/asset.png",
            "contentType": "image/png", "byteSize": target.stat().st_size,
        })
        db.session.commit()

    path = "/api/v1/journey-records/1000/images/img-01"
    assert client.get(path).status_code == 401
    response = client.get(path, headers=headers)

    assert response.status_code == 200
    assert response.data == target.read_bytes()
    assert response.content_type.startswith("image/png")
    assert response.headers["Cache-Control"] == "private"
    assert "inline" in response.headers["Content-Disposition"]


def test_record_image_download_conceals_missing_or_unfinalized_or_invalid_snapshot(client, app, journey_api_db, tmp_path):
    headers, _ = seed(app)
    app.config["RECORD_IMAGE_UPLOAD_DIR"] = str(tmp_path / "record-images")
    path = "/api/v1/journey-records/1000/images/img-01"
    assert_error(client.get(path, headers=headers), 404, "JOURNEY_RECORD_IMAGE_NOT_FOUND")

    with app.app_context():
        record = db.session.get(JourneyRecord, 1000)
        record.status = "finalized"
        record.snapshot = {"schemaVersion": 1}
        db.session.commit()
    response = client.get(path, headers=headers)
    assert_error(response, 500, "JOURNEY_RECORD_SNAPSHOT_INVALID")
    assert str(tmp_path) not in str(response.get_json())


def test_record_image_download_conceals_another_users_record(client, app, journey_api_db, tmp_path):
    headers, _ = seed(app)
    app.config["RECORD_IMAGE_UPLOAD_DIR"] = str(tmp_path / "record-images")
    response = client.get("/api/v1/journey-records/2000/images/img-01", headers=headers)
    assert_error(response, 404, "JOURNEY_RECORD_NOT_FOUND")
