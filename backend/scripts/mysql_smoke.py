import sys
from pathlib import Path

from sqlalchemy import text


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.extensions import db


def main():
    app = create_app("development")

    with app.app_context():
        select_one = db.session.execute(text("SELECT 1")).scalar()
        current_database = db.session.execute(text("SELECT DATABASE()")).scalar()
        dialect = db.engine.dialect.name

        if select_one != 1:
            raise RuntimeError("SELECT 1 failed")
        if current_database != "tonglvji":
            raise RuntimeError("Unexpected current database")
        if dialect != "mysql":
            raise RuntimeError("Unexpected database dialect")

        response = app.test_client().get("/api/v1/health")
        payload = response.get_json()
        if response.status_code != 200:
            raise RuntimeError("Health check failed")
        if payload["data"]["database"]["status"] != "connected":
            raise RuntimeError("Health check database status is not connected")

    print("mysql smoke checks passed")


if __name__ == "__main__":
    main()
