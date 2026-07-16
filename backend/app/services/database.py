from sqlalchemy import text

from app.extensions import db


def check_database_connection():
    db.session.execute(text("SELECT 1")).scalar()
    return {
        "status": "connected",
        "dialect": db.engine.dialect.name,
    }
