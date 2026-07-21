import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db
from app.models import Child, ExplorationPlan, GuideCard, JourneyRecord, Task, TaskSubmission, User
from app.services.journey_records import list_journey_record_models_for_user


def main():
    app = create_app("development")
    with app.app_context():
        assert db.session.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "d2842a9e808b"
        assert "journey_records" in inspect(db.engine).get_table_names()
        models = {"users": User, "children": Child, "exploration_plans": ExplorationPlan, "guide_cards": GuideCard, "tasks": Task, "task_submissions": TaskSubmission, "journey_records": JourneyRecord}
        before = {name: db.session.query(model).count() for name, model in models.items()}
        user = User.query.order_by(User.id.asc()).first()
        records, total = list_journey_record_models_for_user(user) if user else ([], 0)
        after = {name: db.session.query(model).count() for name, model in models.items()}
        assert before == after
        assert not db.session.new and not db.session.dirty and not db.session.deleted
        print(f"journey_records={before['journey_records']}")
        print(f"query_context={'available' if user else 'no-user'}")
        print(f"records_returned={len(records)} total={total}")
        print("service_smoke=passed")


if __name__ == "__main__":
    main()
