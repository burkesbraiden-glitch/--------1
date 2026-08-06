import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import JSON, event, select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Child, ExplorationPlan, JourneyRecord, Task, TaskSubmission, User


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@pytest.fixture()
def journey_record_db(app):
    with app.app_context():
        event.listen(db.engine, "connect", _enable_sqlite_foreign_keys)
        db.engine.dispose()
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()
        event.remove(db.engine, "connect", _enable_sqlite_foreign_keys)
        db.engine.dispose()


def create_plan(plan_id=100):
    user = User(id=1, phone="13800138000", nickname="测试用户")
    child = Child(
        id=10,
        user_id=1,
        name="小探索家",
        age=7,
        age_group="7-12",
        interests=[],
        is_default=True,
    )
    plan = ExplorationPlan(
        id=plan_id,
        user_id=1,
        child_id=10,
        title="测试探索计划",
        destination="测试博物馆",
        age_group="7-12",
        duration="3小时",
        interests=["历史故事"],
    )
    db.session.add_all([user, child, plan])
    db.session.commit()
    return plan


def create_submission(plan_id=100, submission_id=500):
    task = Task(
        id=1000,
        plan_id=plan_id,
        sort_order=1,
        title="观察任务",
        subtitle="找一找小动物",
        age_group="7-12",
        duration="20分钟",
        task_type="观察任务",
        summary="观察屋檐上的小动物。",
        objective="完成观察",
        steps=["抬头观察"],
        questions=["你发现了什么？"],
        record_mode="拍照记录",
        theme="beasts",
    )
    submission = TaskSubmission(
        id=submission_id,
        task_id=1000,
        status="in-progress",
    )
    db.session.add_all([task, submission])
    db.session.commit()
    return submission


def test_journey_record_defaults_nullable_fields_and_relationship(journey_record_db, app):
    with app.app_context():
        plan = create_plan()
        record = JourneyRecord(id=10000, plan_id=plan.id)
        db.session.add(record)
        db.session.commit()

        assert record.status == "draft"
        assert record.custom_title is None
        assert record.summary is None
        assert record.cover_submission_id is None
        assert record.finalized_at is None
        assert record.created_at is not None
        assert record.updated_at is not None
        assert record.plan == plan
        assert plan.journey_record == record


def test_journey_record_plan_id_is_unique(journey_record_db, app):
    with app.app_context():
        plan = create_plan()
        db.session.add(JourneyRecord(id=10000, plan_id=plan.id))
        db.session.commit()

        db.session.add(JourneyRecord(id=10001, plan_id=plan.id))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        assert db.session.scalar(select(JourneyRecord).where(JourneyRecord.plan_id == plan.id)).id == 10000


def test_journey_record_rejects_invalid_status(journey_record_db, app):
    with app.app_context():
        plan = create_plan()
        db.session.add(JourneyRecord(id=10000, plan_id=plan.id, status="archived"))

        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_deleting_plan_cascades_only_its_journey_record(journey_record_db, app):
    with app.app_context():
        first_plan = create_plan(100)
        second_plan = ExplorationPlan(
            id=101,
            user_id=1,
            child_id=10,
            title="另一个探索计划",
            destination="另一个博物馆",
            age_group="7-12",
            duration="2小时",
            interests=["自然"],
        )
        db.session.add(second_plan)
        db.session.add_all(
            [
                JourneyRecord(id=10000, plan_id=first_plan.id),
                JourneyRecord(id=10001, plan_id=second_plan.id),
            ]
        )
        db.session.commit()

        db.session.delete(first_plan)
        db.session.commit()

        assert db.session.get(JourneyRecord, 10000) is None
        assert db.session.get(JourneyRecord, 10001) is not None


def test_deleting_cover_submission_sets_foreign_key_to_null(journey_record_db, app):
    with app.app_context():
        plan = create_plan()
        submission = create_submission(plan.id)
        record = JourneyRecord(
            id=10000,
            plan_id=plan.id,
            cover_submission_id=submission.id,
        )
        db.session.add(record)
        db.session.commit()

        assert record.cover_submission == submission
        db.session.delete(submission)
        db.session.commit()
        db.session.refresh(record)

        assert record.cover_submission_id is None
        assert record.cover_submission is None


def test_journey_record_has_no_future_phase_columns(journey_record_db, app):
    forbidden_columns = {
        "user_id",
        "child_id",
        "image_url",
        "note",
        "completed_at",
        "task_count",
        "photo_count",
        "growth_score",
        "album_json",
        "published_at",
    }

    assert forbidden_columns.isdisjoint(JourneyRecord.__table__.columns.keys())


def test_journey_record_snapshot_is_nullable_json_without_defaults(journey_record_db):
    snapshot = JourneyRecord.__table__.c.snapshot

    assert snapshot.nullable is True
    assert isinstance(snapshot.type, JSON)
    assert snapshot.default is None
    assert snapshot.server_default is None


def test_snapshot_migration_has_a_single_additive_change():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "f6a52a1b2d4_add_snapshot_to_journey_records.py"
    )
    source = migration_path.read_text(encoding="utf-8")

    assert 'revision = "f6a52a1b2d4"' in source
    assert 'down_revision = "e6c5a1f9b2d3"' in source
    assert 'op.add_column("journey_records", sa.Column("snapshot", sa.JSON(), nullable=True))' in source
    assert 'op.drop_column("journey_records", "snapshot")' in source
    assert "server_default" not in source
    assert "UPDATE" not in source
