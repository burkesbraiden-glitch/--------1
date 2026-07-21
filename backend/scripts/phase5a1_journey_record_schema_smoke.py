from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db
from app.models import Child, ExplorationPlan, GuideCard, JourneyRecord, Task, TaskSubmission, User


EXPECTED_REVISION = "d2842a9e808b"
EXISTING_TABLES = {
    "users": User,
    "children": Child,
    "exploration_plans": ExplorationPlan,
    "guide_cards": GuideCard,
    "tasks": Task,
    "task_submissions": TaskSubmission,
}
EXPECTED_COLUMNS = {
    "id": (False, "BIGINT"),
    "plan_id": (False, "BIGINT"),
    "custom_title": (True, "VARCHAR"),
    "summary": (True, "TEXT"),
    "cover_submission_id": (True, "BIGINT"),
    "status": (False, "VARCHAR"),
    "finalized_at": (True, "DATETIME"),
    "created_at": (False, "DATETIME"),
    "updated_at": (False, "DATETIME"),
}


def _foreign_key_matches(foreign_key, column, referred_table, ondelete):
    return (
        foreign_key["constrained_columns"] == [column]
        and foreign_key["referred_table"] == referred_table
        and foreign_key.get("options", {}).get("ondelete", "").upper() == ondelete
    )


def main():
    app = create_app("development")
    with app.app_context():
        inspector = inspect(db.engine)
        table_names = set(inspector.get_table_names())
        missing_tables = (set(EXISTING_TABLES) | {"journey_records"}) - table_names
        assert not missing_tables, f"missing tables: {sorted(missing_tables)}"

        revision = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert revision == EXPECTED_REVISION, f"unexpected revision: {revision}"

        columns = {column["name"]: column for column in inspector.get_columns("journey_records")}
        assert set(columns) == set(EXPECTED_COLUMNS), f"unexpected columns: {sorted(columns)}"
        for name, (nullable, type_name) in EXPECTED_COLUMNS.items():
            assert columns[name]["nullable"] is nullable, f"unexpected nullability for {name}"
            assert type_name in str(columns[name]["type"]).upper(), f"unexpected type for {name}"
        assert columns["status"]["default"] is not None, "status server default is missing"

        unique_constraints = inspector.get_unique_constraints("journey_records")
        assert any(
            constraint["name"] == "plan_journey_record"
            and constraint["column_names"] == ["plan_id"]
            for constraint in unique_constraints
        ), "plan_id unique constraint is missing"

        check_constraints = inspector.get_check_constraints("journey_records")
        assert any(
            constraint["name"] == "ck_journey_records_status_allowed"
            and "draft" in constraint["sqltext"]
            and "finalized" in constraint["sqltext"]
            for constraint in check_constraints
        ), "status check constraint is missing"

        indexes = inspector.get_indexes("journey_records")
        assert any(
            index["name"] == "ix_journey_records_cover_submission_id"
            and index["column_names"] == ["cover_submission_id"]
            and not index["unique"]
            for index in indexes
        ), "cover submission index is missing"

        foreign_keys = inspector.get_foreign_keys("journey_records")
        assert any(
            _foreign_key_matches(foreign_key, "plan_id", "exploration_plans", "CASCADE")
            for foreign_key in foreign_keys
        ), "plan cascade foreign key is missing"
        assert any(
            _foreign_key_matches(foreign_key, "cover_submission_id", "task_submissions", "SET NULL")
            for foreign_key in foreign_keys
        ), "cover submission set-null foreign key is missing"

        print(f"revision={revision}")
        print(f"journey_records={db.session.query(JourneyRecord).count()}")
        for table_name, model in EXISTING_TABLES.items():
            print(f"{table_name}={db.session.query(model).count()}")
        print("journey_record_schema_smoke=passed")


if __name__ == "__main__":
    main()
