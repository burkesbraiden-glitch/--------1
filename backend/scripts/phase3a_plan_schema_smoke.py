import sys
from pathlib import Path

from sqlalchemy import inspect, text


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.extensions import db


EXPECTED_REVISION = "c795c3738e73"
FORBIDDEN_TABLES = {
    "badges",
    "favorites",
    "records",
}


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


def main():
    app = create_app("development")

    with app.app_context():
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())

        for table_name in ("users", "children", "exploration_plans", "guide_cards"):
            if table_name not in tables:
                raise RuntimeError(f"{table_name} table is missing")

        if tables & FORBIDDEN_TABLES:
            raise RuntimeError("Forbidden stage-out table found")

        plan_columns = inspector.get_columns("exploration_plans")
        plan_column_names = {column["name"] for column in plan_columns}
        expected_plan_columns = {
            "id",
            "user_id",
            "child_id",
            "title",
            "destination",
            "age_group",
            "duration",
            "interests",
            "status",
            "created_at",
            "updated_at",
        }
        if plan_column_names != expected_plan_columns:
            raise RuntimeError("exploration_plans columns are incorrect")
        if "task_count" in plan_column_names:
            raise RuntimeError("exploration_plans.task_count must not exist")
        check_json_column(plan_columns, "interests")

        plan_foreign_keys = inspector.get_foreign_keys("exploration_plans")
        user_foreign_key = foreign_key_by_column(plan_foreign_keys, "user_id", "users")
        if user_foreign_key is None:
            raise RuntimeError("exploration_plans.user_id foreign key is missing")
        if user_foreign_key["referred_columns"] != ["id"]:
            raise RuntimeError("exploration_plans.user_id must refer to users.id")
        if user_foreign_key["options"].get("ondelete") != "CASCADE":
            raise RuntimeError("exploration_plans.user_id must use ON DELETE CASCADE")

        child_foreign_key = foreign_key_by_column(plan_foreign_keys, "child_id", "children")
        if child_foreign_key is None:
            raise RuntimeError("exploration_plans.child_id foreign key is missing")
        if child_foreign_key["referred_columns"] != ["id"]:
            raise RuntimeError("exploration_plans.child_id must refer to children.id")
        if child_foreign_key["options"].get("ondelete") != "RESTRICT":
            raise RuntimeError("exploration_plans.child_id must use ON DELETE RESTRICT")

        check_constraint_contains(inspector, "exploration_plans", "age_group")
        check_constraint_contains(inspector, "exploration_plans", "status")

        guide_columns = inspector.get_columns("guide_cards")
        guide_column_names = {column["name"] for column in guide_columns}
        expected_guide_columns = {
            "id",
            "plan_id",
            "child_intro",
            "questions",
            "focus_items",
            "audio_url",
            "created_at",
            "updated_at",
        }
        if guide_column_names != expected_guide_columns:
            raise RuntimeError("guide_cards columns are incorrect")
        if "destination" in guide_column_names:
            raise RuntimeError("guide_cards.destination must not exist")
        for name in ("child_intro", "questions", "focus_items"):
            check_json_column(guide_columns, name)

        guide_foreign_key = foreign_key_by_column(
            inspector.get_foreign_keys("guide_cards"),
            "plan_id",
            "exploration_plans",
        )
        if guide_foreign_key is None:
            raise RuntimeError("guide_cards.plan_id foreign key is missing")
        if guide_foreign_key["referred_columns"] != ["id"]:
            raise RuntimeError("guide_cards.plan_id must refer to exploration_plans.id")
        if guide_foreign_key["options"].get("ondelete") != "CASCADE":
            raise RuntimeError("guide_cards.plan_id must use ON DELETE CASCADE")

        unique_guide_indexes = {
            tuple(index["column_names"])
            for index in inspector.get_indexes("guide_cards")
            if index.get("unique")
        }
        if ("plan_id",) not in unique_guide_indexes:
            raise RuntimeError("guide_cards.plan_id unique index is missing")

        revision = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if revision != EXPECTED_REVISION:
            raise RuntimeError("Alembic revision is not applied")

    print("phase3a plan schema checks passed")


if __name__ == "__main__":
    main()
