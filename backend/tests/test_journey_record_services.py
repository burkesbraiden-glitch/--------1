from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import app.services.journey_records as journey_record_service
from app.extensions import db
from app.models import Child, ExplorationPlan, GuideCard, JourneyRecord, Task, TaskSubmission, User
from app.services.children import ChildError
from app.services.journey_records import (
    JourneyRecordError,
    create_or_get_journey_record,
    finalize_journey_record,
    get_journey_record_model_for_plan,
    get_journey_record_model_for_user,
    list_journey_record_models_for_user,
    serialize_journey_record,
    update_journey_record,
)
from app.utils.time import utc_now


@pytest.fixture()
def service_db(app):
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def seed_record(user_id=1, child_id=10, plan_id=100, record_id=1000, *, status="draft"):
    user = db.session.get(User, user_id)
    child = db.session.get(Child, child_id)
    if user is None:
        user = User(id=user_id, phone=f"1380000{user_id:04d}", nickname=f"user-{user_id}")
        db.session.add(user)
    if child is None:
        child = Child(id=child_id, user_id=user_id, name="child", age=7, age_group="7-12", interests=[], is_default=True)
        db.session.add(child)
    plan = ExplorationPlan(id=plan_id, user_id=user_id, child_id=child_id, title="plan title", destination="museum", age_group="7-12", duration="3h", interests=[])
    record = JourneyRecord(id=record_id, plan_id=plan_id, status=status)
    db.session.add_all([plan, record])
    db.session.commit()
    return user, plan, record


def add_task(plan_id, task_id, order, *, submission=None):
    task = Task(id=task_id, plan_id=plan_id, sort_order=order, title=f"task-{order}", subtitle="subtitle", age_group="7-12", duration="20m", task_type="observe", summary="summary", objective="objective", steps=[], questions=[], record_mode="note", theme=None)
    db.session.add(task)
    if submission is not None:
        db.session.add(TaskSubmission(id=task_id + 10000, task_id=task_id, **submission))
    db.session.commit()


def test_get_record_for_owner_and_hides_other_users(service_db, app):
    with app.app_context():
        user, plan, record = seed_record()
        other, _, other_record = seed_record(2, 20, 200, 2000)

        assert get_journey_record_model_for_user(user, record.id).id == record.id
        with pytest.raises(JourneyRecordError) as error:
            get_journey_record_model_for_user(user, other_record.id)
        assert error.value.code == "JOURNEY_RECORD_NOT_FOUND"
        assert get_journey_record_model_for_plan(user, plan.id).id == record.id


def test_list_filters_validates_and_orders_records(service_db, app):
    with app.app_context():
        user, _, first = seed_record()
        _, second_plan, second = seed_record(1, 10, 101, 1001, status="finalized")
        second.updated_at = utc_now() + timedelta(minutes=1)
        db.session.commit()
        other, _, _ = seed_record(2, 20, 200, 2000)

        records, total = list_journey_record_models_for_user(user, child_id=10, limit=1, offset=0)
        assert total == 2
        assert [record.id for record in records] == [second.id]
        assert list_journey_record_models_for_user(user, status="draft")[1] == 1
        with pytest.raises(JourneyRecordError):
            list_journey_record_models_for_user(user, status="invalid")
        with pytest.raises(JourneyRecordError):
            list_journey_record_models_for_user(user, limit=0)
        with pytest.raises(ChildError):
            list_journey_record_models_for_user(user, child_id=other.children[0].id)


def test_serialization_aggregates_entries_and_hides_storage_keys(service_db, app):
    with app.app_context():
        _, plan, record = seed_record()
        add_task(plan.id, 1, 2, submission={"status": "in-progress", "image_url": None, "note": " observation ", "completed_at": None})
        add_task(plan.id, 2, 1, submission={"status": "completed", "image_url": "private/key.jpg", "note": "done", "completed_at": utc_now()})
        add_task(plan.id, 3, 3)
        record.cover_submission_id = 10002
        record.custom_title = " custom "
        db.session.commit()

        payload = serialize_journey_record(get_journey_record_model_for_plan(plan.user, plan.id))
        assert payload["displayTitle"] == " custom "
        assert (payload["taskCount"], payload["completedTaskCount"], payload["photoCount"], payload["noteCount"]) == (3, 1, 1, 2)
        assert [entry["taskId"] for entry in payload["entries"]] == [2, 1]
        assert payload["entries"][0]["imageUrl"].endswith("/plans/100/tasks/2/submission/image")
        assert "private/key.jpg" not in str(payload)
        assert payload["coverImageUrl"].endswith("/plans/100/tasks/2/submission/image")
        assert "entries" not in serialize_journey_record(get_journey_record_model_for_plan(plan.user, plan.id), include_entries=False)


def test_missing_record_and_plan_without_record_do_not_create_data(service_db, app):
    with app.app_context():
        user, plan, record = seed_record(11, 110, 1100, 11000)
        before = JourneyRecord.query.count()
        with pytest.raises(JourneyRecordError) as missing:
            get_journey_record_model_for_user(user, 999999)
        assert missing.value.code == "JOURNEY_RECORD_NOT_FOUND"
        empty_plan = ExplorationPlan(id=1101, user_id=user.id, child_id=plan.child_id, title="empty", destination="museum", age_group="7-12", duration="1h", interests=[])
        db.session.add(empty_plan); db.session.commit()
        with pytest.raises(JourneyRecordError) as absent:
            get_journey_record_model_for_plan(user, empty_plan.id)
        assert absent.value.code == "JOURNEY_RECORD_NOT_FOUND"
        assert JourneyRecord.query.count() == before


def test_plan_ownership_and_list_isolation(service_db, app):
    with app.app_context():
        user, _, own = seed_record(12, 120, 1200, 12000)
        other, other_plan, other_record = seed_record(13, 130, 1300, 13000)
        with pytest.raises(Exception) as error:
            get_journey_record_model_for_plan(user, other_plan.id)
        assert getattr(error.value, "code", None) == "PLAN_NOT_FOUND"
        records, total = list_journey_record_models_for_user(user)
        assert total == 1 and [item.id for item in records] == [own.id]
        assert all(item.plan.user_id == user.id for item in records)
        assert other_record.id not in [item.id for item in records]


@pytest.mark.parametrize("kwargs", [{"limit": 101}, {"offset": -1}, {"limit": "1"}, {"offset": "0"}])
def test_list_rejects_invalid_pagination(service_db, app, kwargs):
    with app.app_context():
        user, _, _ = seed_record(14, 140, 1400, 14000)
        with pytest.raises(JourneyRecordError) as error:
            list_journey_record_models_for_user(user, **kwargs)
        assert error.value.code == "VALIDATION_ERROR"


def test_list_finalized_filter_and_pagination(service_db, app):
    with app.app_context():
        user, _, draft = seed_record(15, 150, 1500, 15000)
        _, _, finalized = seed_record(15, 150, 1501, 15001, status="finalized")
        finalized.updated_at = draft.updated_at
        db.session.commit()
        records, total = list_journey_record_models_for_user(user, status="finalized", limit=1, offset=0)
        assert total == 1 and [item.id for item in records] == [finalized.id]
        records, total = list_journey_record_models_for_user(user, limit=1, offset=1)
        assert total == 2 and len(records) == 1


def test_empty_record_and_title_fallbacks(service_db, app):
    with app.app_context():
        _, plan, record = seed_record(16, 160, 1600, 16000)
        payload = serialize_journey_record(record)
        assert (payload["taskCount"], payload["completedTaskCount"], payload["photoCount"], payload["noteCount"], payload["entries"], payload["coverImageUrl"]) == (0, 0, 0, 0, [], None)
        for title in (None, "", "   "):
            record.custom_title = title
            assert serialize_journey_record(record)["displayTitle"] == plan.title
        record.custom_title = "custom"
        assert serialize_journey_record(record)["displayTitle"] == "custom"


def test_aggregation_entry_rules_json_and_read_only(service_db, app):
    with app.app_context():
        user, plan, record = seed_record(17, 170, 1700, 17000)
        add_task(plan.id, 171, 1, submission={"status": "completed", "image_url": None, "note": "", "completed_at": utc_now()})
        add_task(plan.id, 172, 2, submission={"status": "in-progress", "image_url": "secret/storage-key.jpg", "note": "", "completed_at": None})
        add_task(plan.id, 173, 3, submission={"status": "in-progress", "image_url": None, "note": "note", "completed_at": None})
        add_task(plan.id, 174, 4, submission={"status": "in-progress", "image_url": None, "note": "   ", "completed_at": None})
        payload = serialize_journey_record(get_journey_record_model_for_plan(user, plan.id))
        assert (payload["taskCount"], payload["completedTaskCount"], payload["photoCount"], payload["noteCount"]) == (4, 1, 1, 1)
        assert [entry["taskId"] for entry in payload["entries"]] == [171, 172, 173]
        assert "secret/storage-key.jpg" not in str(payload)
        assert payload["entries"][1]["imageUrl"].endswith("/submission/image")
        assert payload["createdAt"].endswith("Z") and payload["entries"][0]["completedAt"].endswith("Z")
        assert not {"plan_id", "child_id", "image_url", "_sa_instance_state"} & set(payload)
        no_entries = serialize_journey_record(record, include_entries=False)
        assert "entries" not in no_entries and no_entries["taskCount"] == 4
        assert not db.session.new and not db.session.dirty and not db.session.deleted


def test_cross_plan_cover_is_hidden_without_mutating_record(service_db, app):
    with app.app_context():
        user, plan_a, record = seed_record(18, 180, 1800, 18000)
        _, plan_b, _ = seed_record(18, 180, 1801, 18001)
        add_task(plan_b.id, 181, 1, submission={"status": "completed", "image_url": "secret/other.jpg", "note": "", "completed_at": utc_now()})
        record.cover_submission_id = 10181
        db.session.commit()
        payload = serialize_journey_record(get_journey_record_model_for_user(user, record.id))
        assert payload["coverSubmissionId"] == 10181 and payload["coverImageUrl"] is None
        assert record.cover_submission_id == 10181


def remove_record(record):
    db.session.delete(record)
    db.session.commit()


def business_table_counts():
    return {
        "users": User.query.count(),
        "children": Child.query.count(),
        "plans": ExplorationPlan.query.count(),
        "guide_cards": GuideCard.query.count(),
        "tasks": Task.query.count(),
        "submissions": TaskSubmission.query.count(),
        "journey_records": JourneyRecord.query.count(),
    }


@pytest.mark.parametrize("status", ["ready", "in-progress", "completed"])
def test_create_or_get_creates_draft_record_for_allowed_plan_status(service_db, app, status):
    with app.app_context():
        user, plan, record = seed_record(30, 300, 3000, 30000)
        remove_record(record)
        plan.status = status
        db.session.commit()

        created_record, created = create_or_get_journey_record(user, plan.id)

        assert created is True
        assert created_record.plan_id == plan.id
        assert created_record.status == "draft"
        assert created_record.finalized_at is None
        assert JourneyRecord.query.count() == 1


def test_create_or_get_reuses_existing_record_without_changing_it(service_db, app):
    with app.app_context():
        user, plan, record = seed_record(31, 310, 3100, 31000)
        plan.status = "ready"
        record.custom_title = "已有标题"
        record.summary = "已有总结"
        before_updated_at = record.updated_at
        db.session.commit()

        result, created = create_or_get_journey_record(user, plan.id)

        assert created is False
        assert result.id == record.id
        assert result.custom_title == "已有标题"
        assert result.summary == "已有总结"
        assert result.updated_at == before_updated_at
        assert JourneyRecord.query.count() == 1


def test_create_or_get_rejects_draft_and_other_users_plans(service_db, app):
    with app.app_context():
        user, draft_plan, draft_record = seed_record(32, 320, 3200, 32000)
        remove_record(draft_record)
        other, other_plan, other_record = seed_record(33, 330, 3300, 33000)
        remove_record(other_record)

        with pytest.raises(Exception) as draft_error:
            create_or_get_journey_record(user, draft_plan.id)
        with pytest.raises(Exception) as owner_error:
            create_or_get_journey_record(user, other_plan.id)

        assert getattr(draft_error.value, "code", None) == "PLAN_NOT_READY"
        assert getattr(owner_error.value, "code", None) == "PLAN_NOT_FOUND"
        assert JourneyRecord.query.count() == 0


def test_create_or_get_recovers_from_unique_constraint_race(service_db, app, monkeypatch):
    with app.app_context():
        user, plan, record = seed_record(34, 340, 3400, 34000)
        remove_record(record)
        plan.status = "ready"
        db.session.commit()
        original_commit = db.session.commit

        def concurrent_commit():
            db.session.rollback()
            db.session.add(JourneyRecord(id=34001, plan_id=plan.id))
            original_commit()
            raise IntegrityError(
                "insert",
                {},
                Exception("UNIQUE constraint failed: journey_records.plan_id"),
            )

        monkeypatch.setattr(db.session, "commit", concurrent_commit)
        result, created = create_or_get_journey_record(user, plan.id)

        assert created is False
        assert result.plan_id == plan.id
        assert JourneyRecord.query.count() == 1
        assert db.session.get(ExplorationPlan, plan.id) is not None


def test_create_or_get_reports_database_error_when_race_cannot_be_recovered(service_db, app, monkeypatch):
    with app.app_context():
        user, plan, record = seed_record(35, 350, 3500, 35000)
        remove_record(record)
        plan.status = "ready"
        db.session.commit()

        def fail_commit():
            raise IntegrityError("insert", {}, Exception("duplicate"))

        monkeypatch.setattr(db.session, "commit", fail_commit)
        with pytest.raises(JourneyRecordError) as error:
            create_or_get_journey_record(user, plan.id)

        assert error.value.code == "DATABASE_ERROR"
        assert JourneyRecord.query.count() == 0
        assert db.session.get(ExplorationPlan, plan.id) is not None


def test_create_or_get_does_not_treat_non_unique_integrity_error_as_idempotency(service_db, app, monkeypatch):
    with app.app_context():
        user, plan, existing = seed_record(351, 3510, 35100, 351000)
        plan.status = "ready"
        db.session.commit()
        lookups = [None, existing]
        monkeypatch.setattr(
            journey_record_service,
            "_find_journey_record_model_for_owned_plan",
            lambda *_args: lookups.pop(0),
        )

        def fail_commit():
            raise IntegrityError("insert", {}, Exception("FOREIGN KEY constraint failed"))

        monkeypatch.setattr(db.session, "commit", fail_commit)
        with pytest.raises(JourneyRecordError) as error:
            create_or_get_journey_record(user, plan.id)

        assert error.value.code == "DATABASE_ERROR"
        assert lookups == [existing]
        assert db.session.get(ExplorationPlan, plan.id) is not None


def test_update_normalizes_text_and_only_changes_provided_fields(service_db, app):
    with app.app_context():
        user, plan, record = seed_record(36, 360, 3600, 36000)
        record.summary = "保留原摘要"
        db.session.commit()

        updated = update_journey_record(user, plan.id, {"customTitle": "  中文标题  "})
        assert updated.custom_title == "中文标题"
        assert updated.summary == "保留原摘要"

        updated = update_journey_record(user, plan.id, {"summary": "  第一行\n  第二行  "})
        assert updated.summary == "第一行\n  第二行"
        assert plan.title == "plan title"


@pytest.mark.parametrize("field", ["customTitle", "summary"])
@pytest.mark.parametrize("value", [None, "", "   "])
def test_update_clears_null_and_blank_text(service_db, app, field, value):
    with app.app_context():
        user, plan, record = seed_record(37, 370, 3700, 37000)
        record.custom_title = "旧标题"
        record.summary = "旧摘要"
        db.session.commit()

        updated = update_journey_record(user, plan.id, {field: value})

        assert getattr(updated, "custom_title" if field == "customTitle" else "summary") is None


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({}, "VALIDATION_ERROR"),
        ([], "VALIDATION_ERROR"),
        ({"unknown": "x"}, "VALIDATION_ERROR"),
        ({"custom_title": "x"}, "VALIDATION_ERROR"),
        ({"status": "finalized"}, "VALIDATION_ERROR"),
        ({"finalizedAt": "x"}, "VALIDATION_ERROR"),
        ({"customTitle": 1}, "VALIDATION_ERROR"),
        ({"summary": 1}, "VALIDATION_ERROR"),
        ({"customTitle": "x" * 121}, "VALIDATION_ERROR"),
        ({"summary": "x" * 2001}, "VALIDATION_ERROR"),
    ],
)
def test_update_rejects_invalid_payloads_without_writing(service_db, app, payload, code):
    with app.app_context():
        user, plan, record = seed_record(38, 380, 3800, 38000)
        before = (record.custom_title, record.summary, record.cover_submission_id)

        with pytest.raises(JourneyRecordError) as error:
            update_journey_record(user, plan.id, payload)

        assert error.value.code == code
        assert (record.custom_title, record.summary, record.cover_submission_id) == before


def test_update_validates_cover_belongs_to_plan_has_image_and_hides_storage_key(service_db, app):
    with app.app_context():
        user, plan, record = seed_record(39, 390, 3900, 39000)
        add_task(plan.id, 391, 1, submission={"status": "in-progress", "image_url": "private/cover.jpg", "note": "", "completed_at": None})
        _, other_plan, _ = seed_record(39, 390, 3901, 39001)
        add_task(other_plan.id, 392, 1, submission={"status": "completed", "image_url": "private/other.jpg", "note": "", "completed_at": utc_now()})
        add_task(plan.id, 393, 2, submission={"status": "in-progress", "image_url": None, "note": "", "completed_at": None})

        updated = update_journey_record(user, plan.id, {"coverSubmissionId": 10391})
        assert updated.cover_submission_id == 10391
        serialized = serialize_journey_record(updated)
        assert serialized["coverImageUrl"].endswith("/plans/3900/tasks/391/submission/image")
        assert "private/cover.jpg" not in str(serialized)

        for value in (True, "10391", 0, -1, 10392, 10393, 999999):
            with pytest.raises(JourneyRecordError) as error:
                update_journey_record(user, plan.id, {"coverSubmissionId": value})
            assert error.value.code in {"VALIDATION_ERROR", "INVALID_COVER_SUBMISSION"}

        assert update_journey_record(user, plan.id, {"coverSubmissionId": None}).cover_submission_id is None


def test_update_skips_commit_when_normalized_values_are_unchanged(service_db, app, monkeypatch):
    with app.app_context():
        user, plan, record = seed_record(40, 400, 4000, 40000)
        record.custom_title = None
        record.summary = "摘要"
        db.session.commit()
        before_updated_at = record.updated_at

        def unexpected_commit():
            raise AssertionError("commit must not run")

        monkeypatch.setattr(db.session, "commit", unexpected_commit)
        updated = update_journey_record(user, plan.id, {"customTitle": "   ", "summary": "摘要"})

        assert updated.id == record.id
        assert updated.updated_at == before_updated_at


def test_update_rolls_back_database_error_and_keeps_session_usable(service_db, app, monkeypatch):
    with app.app_context():
        user, plan, record = seed_record(401, 4010, 40100, 401000)
        record.summary = "提交前摘要"
        db.session.commit()

        def fail_commit():
            raise SQLAlchemyError("commit failed")

        monkeypatch.setattr(db.session, "commit", fail_commit)
        with pytest.raises(JourneyRecordError) as error:
            update_journey_record(user, plan.id, {"summary": "不会保存"})

        assert error.value.code == "DATABASE_ERROR"
        assert db.session.get(JourneyRecord, record.id).summary == "提交前摘要"
        assert db.session.get(ExplorationPlan, plan.id) is not None


def test_update_rejects_finalized_record_and_does_not_change_other_models(service_db, app):
    with app.app_context():
        user, plan, record = seed_record(41, 410, 4100, 41000, status="finalized")
        record.finalized_at = utc_now()
        db.session.commit()
        before_plan_status = plan.status

        with pytest.raises(JourneyRecordError) as error:
            update_journey_record(user, plan.id, {"summary": "不能修改"})

        assert error.value.code == "JOURNEY_RECORD_FINALIZED"
        assert plan.status == before_plan_status


def test_finalize_is_idempotent_and_does_not_change_plan_or_submissions(service_db, app, monkeypatch):
    with app.app_context():
        user, plan, record = seed_record(42, 420, 4200, 42000)
        plan.status = "in-progress"
        add_task(plan.id, 421, 1, submission={"status": "in-progress", "image_url": "private/photo.jpg", "note": "发现", "completed_at": None})
        submission = TaskSubmission.query.filter_by(task_id=421).one()
        before_submission = (submission.status, submission.image_url, submission.note, submission.completed_at)
        db.session.commit()

        finalized, finalized_now = finalize_journey_record(user, plan.id)
        assert finalized_now is True
        assert finalized.status == "finalized"
        assert finalized.finalized_at is not None
        finalized_at = finalized.finalized_at
        updated_at = finalized.updated_at

        def unexpected_commit():
            raise AssertionError("repeat finalize must not commit")

        monkeypatch.setattr(db.session, "commit", unexpected_commit)
        repeated, finalized_now = finalize_journey_record(user, plan.id)

        assert finalized_now is False
        assert repeated.finalized_at == finalized_at
        assert repeated.updated_at == updated_at
        assert plan.status == "in-progress"
        assert (submission.status, submission.image_url, submission.note, submission.completed_at) == before_submission


def test_finalize_missing_record_and_database_failure_roll_back(service_db, app, monkeypatch):
    with app.app_context():
        user, plan, record = seed_record(43, 430, 4300, 43000)
        remove_record(record)
        with pytest.raises(JourneyRecordError) as missing:
            finalize_journey_record(user, plan.id)
        assert missing.value.code == "JOURNEY_RECORD_NOT_FOUND"

        record = JourneyRecord(id=43001, plan_id=plan.id)
        db.session.add(record)
        db.session.commit()

        def fail_commit():
            raise SQLAlchemyError("commit failed")

        monkeypatch.setattr(db.session, "commit", fail_commit)
        with pytest.raises(JourneyRecordError) as error:
            finalize_journey_record(user, plan.id)

        assert error.value.code == "DATABASE_ERROR"
        db.session.rollback()
        assert db.session.get(ExplorationPlan, plan.id) is not None


def test_write_services_change_only_journey_records(service_db, app):
    with app.app_context():
        user, plan, record = seed_record(44, 440, 4400, 44000)
        remove_record(record)
        plan.status = "ready"
        db.session.commit()
        before_create = business_table_counts()

        record, created = create_or_get_journey_record(user, plan.id)

        assert created is True
        assert business_table_counts() == {
            **before_create,
            "journey_records": before_create["journey_records"] + 1,
        }
        plan_snapshot = (plan.title, plan.status)
        before_update = business_table_counts()
        update_journey_record(user, plan.id, {"customTitle": "只改记录"})
        assert business_table_counts() == before_update
        assert (plan.title, plan.status) == plan_snapshot

        before_finalize = business_table_counts()
        finalized, finalized_now = finalize_journey_record(user, plan.id)
        assert finalized.id == record.id and finalized_now is True
        assert business_table_counts() == before_finalize
        assert (plan.title, plan.status) == plan_snapshot
