import sys
from pathlib import Path

from sqlalchemy import inspect, text


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.extensions import db


EXPECTED_TABLES = {
    "alembic_version",
    "children",
    "exploration_plans",
    "guide_cards",
    "task_submissions",
    "tasks",
    "users",
}
EXPECTED_REVISION = "c795c3738e73"
FORBIDDEN_TABLES = {"badges", "favorites", "records"}


def column_by_name(columns, name):
    return next(column for column in columns if column["name"] == name)


def main():
    app = create_app("development")

    with app.app_context():
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        missing_tables = EXPECTED_TABLES - tables
        if missing_tables:
            raise RuntimeError("Expected business table is missing")
        if tables & FORBIDDEN_TABLES:
            raise RuntimeError("Unexpected business tables found")

        if "users" not in tables:
            raise RuntimeError("users table is missing")
        if "children" not in tables:
            raise RuntimeError("children table is missing")

        user_columns = inspector.get_columns("users")
        user_column_names = {column["name"] for column in user_columns}
        if "age" in user_column_names:
            raise RuntimeError("users.age must not exist")
        if column_by_name(user_columns, "phone")["nullable"] is not True:
            raise RuntimeError("users.phone must be nullable")

        user_indexes = inspector.get_indexes("users")
        unique_user_indexes = {
            tuple(index["column_names"])
            for index in user_indexes
            if index.get("unique")
        }
        if ("phone",) not in unique_user_indexes:
            raise RuntimeError("users.phone unique index is missing")
        if ("wechat_openid",) not in unique_user_indexes:
            raise RuntimeError("users.wechat_openid unique index is missing")

        child_columns = inspector.get_columns("children")
        child_column_names = {column["name"] for column in child_columns}
        if "age_group" not in child_column_names:
            raise RuntimeError("children.age_group is missing")
        if str(column_by_name(child_columns, "interests")["type"]).upper() != "JSON":
            raise RuntimeError("children.interests must be JSON")

        foreign_keys = inspector.get_foreign_keys("children")
        user_foreign_key = next(
            (
                foreign_key
                for foreign_key in foreign_keys
                if foreign_key["constrained_columns"] == ["user_id"]
                and foreign_key["referred_table"] == "users"
                and foreign_key["referred_columns"] == ["id"]
            ),
            None,
        )
        if user_foreign_key is None:
            raise RuntimeError("children.user_id foreign key is missing")
        if user_foreign_key["options"].get("ondelete") != "CASCADE":
            raise RuntimeError("children.user_id must use ON DELETE CASCADE")

        revision = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if revision != EXPECTED_REVISION:
            raise RuntimeError("Alembic revision is not applied")

    print("phase2a schema checks passed")


if __name__ == "__main__":
    main()
