from sqlalchemy import CheckConstraint, JSON, UniqueConstraint

from app import create_app
from app.extensions import db
from app.models import Child, ExplorationPlan, GuideCard, Task, TaskSubmission, User


def _check_sql(table):
    return {
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }


def _unique_columns(table):
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def _assert_list_default(column):
    assert callable(column.default.arg)
    assert column.default.arg(None) == []
    assert column.default.arg(None) is not column.default.arg(None)


def test_task_tables_are_registered():
    create_app("testing")

    assert "tasks" in db.metadata.tables
    assert "task_submissions" in db.metadata.tables


def test_task_columns_are_content_only():
    table = Task.__table__

    assert set(table.c.keys()) == {
        "id",
        "plan_id",
        "sort_order",
        "title",
        "subtitle",
        "age_group",
        "duration",
        "task_type",
        "summary",
        "objective",
        "steps",
        "questions",
        "record_mode",
        "theme",
        "created_at",
        "updated_at",
    }
    for forbidden_column in ("status", "record", "image_path", "note", "user_id", "child_id", "points", "illustration"):
        assert forbidden_column not in table.c

    assert table.c.id.primary_key is True
    assert table.c.plan_id.nullable is False
    assert table.c.plan_id.index is True
    assert table.c.sort_order.nullable is False
    assert table.c.title.nullable is False
    assert table.c.title.type.length == 120
    assert table.c.subtitle.nullable is True
    assert table.c.subtitle.type.length == 240
    assert table.c.age_group.nullable is False
    assert table.c.age_group.type.length == 16
    assert table.c.duration.nullable is False
    assert table.c.duration.type.length == 32
    assert table.c.task_type.nullable is False
    assert table.c.task_type.type.length == 32
    assert table.c.summary.nullable is True
    assert table.c.objective.nullable is False
    assert table.c.steps.nullable is False
    assert isinstance(table.c.steps.type, JSON)
    _assert_list_default(table.c.steps)
    assert table.c.questions.nullable is False
    assert isinstance(table.c.questions.type, JSON)
    _assert_list_default(table.c.questions)
    assert table.c.record_mode.nullable is False
    assert table.c.record_mode.type.length == 255
    assert table.c.theme.nullable is True
    assert table.c.theme.type.length == 32
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False


def test_task_constraints_and_foreign_key():
    table = Task.__table__
    foreign_keys = list(table.c.plan_id.foreign_keys)

    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "exploration_plans.id"
    assert foreign_keys[0].ondelete == "CASCADE"
    assert ("plan_id", "sort_order") in _unique_columns(table)

    check_sql = _check_sql(table)
    assert "sort_order >= 1" in check_sql
    assert "age_group IN ('3-6', '7-12')" in check_sql


def test_task_submission_columns_are_submission_state_only():
    table = TaskSubmission.__table__

    assert set(table.c.keys()) == {
        "id",
        "task_id",
        "status",
        "image_url",
        "note",
        "completed_at",
        "created_at",
        "updated_at",
    }
    for forbidden_column in ("user_id", "child_id", "plan_id"):
        assert forbidden_column not in table.c

    assert table.c.id.primary_key is True
    assert table.c.task_id.nullable is False
    assert table.c.task_id.unique is True
    assert table.c.task_id.index is True
    assert table.c.status.nullable is False
    assert table.c.status.type.length == 24
    assert table.c.image_url.nullable is True
    assert table.c.image_url.type.length == 500
    assert table.c.note.nullable is True
    assert table.c.completed_at.nullable is True
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False


def test_task_submission_constraints_and_foreign_key():
    table = TaskSubmission.__table__
    foreign_keys = list(table.c.task_id.foreign_keys)

    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "tasks.id"
    assert foreign_keys[0].ondelete == "CASCADE"

    check_sql = _check_sql(table)
    assert "status IN ('in-progress', 'completed')" in check_sql
    assert all("not-started" not in sql for sql in check_sql)


def test_task_relationships_are_configured():
    assert ExplorationPlan.tasks.property.mapper.class_ is Task
    assert ExplorationPlan.tasks.property.back_populates == "plan"
    assert "delete-orphan" in ExplorationPlan.tasks.property.cascade
    assert ExplorationPlan.tasks.property.passive_deletes is True

    assert Task.plan.property.mapper.class_ is ExplorationPlan
    assert Task.plan.property.back_populates == "tasks"
    assert Task.submission.property.mapper.class_ is TaskSubmission
    assert Task.submission.property.uselist is False
    assert Task.submission.property.back_populates == "task"
    assert "delete-orphan" in Task.submission.property.cascade
    assert Task.submission.property.passive_deletes is True

    assert TaskSubmission.task.property.mapper.class_ is Task
    assert TaskSubmission.task.property.back_populates == "submission"


def test_existing_business_model_fields_are_unchanged():
    assert set(User.__table__.c.keys()) == {
        "id",
        "phone",
        "nickname",
        "city",
        "wechat_openid",
        "created_at",
        "updated_at",
    }
    assert set(Child.__table__.c.keys()) == {
        "id",
        "user_id",
        "name",
        "age",
        "city",
        "age_group",
        "interests",
        "is_default",
        "created_at",
        "updated_at",
    }
    assert set(ExplorationPlan.__table__.c.keys()) == {
        "id",
        "user_id",
        "child_id",
        "route_stop_id",
        "title",
        "destination",
        "age_group",
        "duration",
        "interests",
        "status",
        "completed_at",
        "source_snapshot",
        "created_at",
        "updated_at",
    }
    assert set(GuideCard.__table__.c.keys()) == {
        "id",
        "plan_id",
        "child_intro",
        "questions",
        "focus_items",
        "audio_url",
        "created_at",
        "updated_at",
    }
