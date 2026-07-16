import sys
from pathlib import Path

from sqlalchemy import inspect, text


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.extensions import db


EXPECTED_REVISION = "c795c3738e73"
REQUIRED_TABLES = {
    "children",
    "exploration_plans",
    "guide_cards",
    "task_submissions",
    "tasks",
    "users",
}
FORBIDDEN_TABLES = {"badges", "favorites", "records"}


def column_by_name(columns, name):
    return next(column for column in columns if column["name"] == name)


def foreign_key_by_column(foreign_keys, column_name, referred_table):
    return next(
        (
            foreign_key
            for foreign_key in foreign_keys
            if foreign_key["constrained_columns"] == [column_name]
            and foreign_key["referred_table"] == referred_table
        ),
        None,
    )


def check_json_column(columns, name):
    column_type = str(column_by_name(columns, name)["type"]).upper()
    if column_type != "JSON":
        raise RuntimeError(f"{name} must be JSON")


def check_constraint_contains(inspector, table_name, required_sql):
    constraints = inspector.get_check_constraints(table_name)
    if not any(required_sql in constraint.get("sqltext", "") for constraint in constraints):
        raise RuntimeError(f"{table_name} check constraint is missing")


def unique_index_columns(inspector, table_name):
    return {
        tuple(index["column_names"])
        for index in inspector.get_indexes(table_name)
        if index.get("unique")
    }


def main():
    app = create_app("development")

    with app.app_context():
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())

        missing_tables = REQUIRED_TABLES - tables
        if missing_tables:
            raise RuntimeError("Required table is missing")
        if tables & FORBIDDEN_TABLES:
            raise RuntimeError("Forbidden stage-out table found")

        task_columns = inspector.get_columns("tasks")
        task_column_names = {column["name"] for column in task_columns}
        expected_task_columns = {
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
        if task_column_names != expected_task_columns:
            raise RuntimeError("tasks columns are incorrect")
        for forbidden_column in ("status", "record", "image_path", "note", "user_id", "child_id"):
            if forbidden_column in task_column_names:
                raise RuntimeError("tasks contains a forbidden column")
        check_json_column(task_columns, "steps")
        check_json_column(task_columns, "questions")

        task_plan_foreign_key = foreign_key_by_column(
            inspector.get_foreign_keys("tasks"),
            "plan_id",
            "exploration_plans",
        )
        if task_plan_foreign_key is None:
            raise RuntimeError("tasks.plan_id foreign key is missing")
        if task_plan_foreign_key["referred_columns"] != ["id"]:
            raise RuntimeError("tasks.plan_id must refer to exploration_plans.id")
        if task_plan_foreign_key["options"].get("ondelete") != "CASCADE":
            raise RuntimeError("tasks.plan_id must use ON DELETE CASCADE")

        if ("plan_id", "sort_order") not in unique_index_columns(inspector, "tasks"):
            raise RuntimeError("tasks plan_id/sort_order unique index is missing")
        check_constraint_contains(inspector, "tasks", "age_group")
        check_constraint_contains(inspector, "tasks", "sort_order")

        submission_columns = inspector.get_columns("task_submissions")
        submission_column_names = {column["name"] for column in submission_columns}
        expected_submission_columns = {
            "id",
            "task_id",
            "status",
            "image_url",
            "note",
            "completed_at",
            "created_at",
            "updated_at",
        }
        if submission_column_names != expected_submission_columns:
            raise RuntimeError("task_submissions columns are incorrect")
        for forbidden_column in ("user_id", "child_id", "plan_id"):
            if forbidden_column in submission_column_names:
                raise RuntimeError("task_submissions contains a forbidden column")

        submission_task_foreign_key = foreign_key_by_column(
            inspector.get_foreign_keys("task_submissions"),
            "task_id",
            "tasks",
        )
        if submission_task_foreign_key is None:
            raise RuntimeError("task_submissions.task_id foreign key is missing")
        if submission_task_foreign_key["referred_columns"] != ["id"]:
            raise RuntimeError("task_submissions.task_id must refer to tasks.id")
        if submission_task_foreign_key["options"].get("ondelete") != "CASCADE":
            raise RuntimeError("task_submissions.task_id must use ON DELETE CASCADE")

        if ("task_id",) not in unique_index_columns(inspector, "task_submissions"):
            raise RuntimeError("task_submissions.task_id unique index is missing")
        check_constraint_contains(inspector, "task_submissions", "status")

        revision = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if revision != EXPECTED_REVISION:
            raise RuntimeError("Alembic revision is not applied")

    print("phase4a task schema checks passed")


if __name__ == "__main__":
    main()
