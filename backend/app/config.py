from datetime import timedelta
import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


def _split_origins(value):
    return [origin.strip() for origin in value.split(",") if origin.strip()]


_PRODUCTION_SECRET_FIELDS = ("SECRET_KEY", "JWT_SECRET_KEY")
_PRODUCTION_SECRET_PLACEHOLDERS = {"replace-me", "changeme"}
_MINIMUM_PRODUCTION_SECRET_LENGTH = 32


def validate_production_config(config):
    if config["APP_ENV"] != "production":
        return

    for field_name in _PRODUCTION_SECRET_FIELDS:
        value = config.get(field_name)
        normalized_value = value.strip() if isinstance(value, str) else ""

        if (
            not normalized_value
            or normalized_value.casefold() in _PRODUCTION_SECRET_PLACEHOLDERS
            or len(normalized_value) < _MINIMUM_PRODUCTION_SECRET_LENGTH
        ):
            raise RuntimeError(f"Invalid production configuration: {field_name}")


class BaseConfig:
    APP_ENV = os.getenv("APP_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY", "replace-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "replace-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://username:password@127.0.0.1:3306/tonglvji?charset=utf8mb4",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }
    CORS_ORIGINS = _split_origins(os.getenv("CORS_ORIGINS", "http://localhost:5173"))
    JWT_ACCESS_TOKEN_HOURS = int(os.getenv("JWT_ACCESS_TOKEN_HOURS", "168"))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=JWT_ACCESS_TOKEN_HOURS)
    TASK_IMAGE_UPLOAD_DIR = os.getenv(
        "TASK_IMAGE_UPLOAD_DIR",
        str(BACKEND_DIR / "var" / "uploads" / "task-images"),
    )
    TASK_IMAGE_MAX_BYTES = int(os.getenv("TASK_IMAGE_MAX_BYTES", str(10 * 1024 * 1024)))
    RECORD_IMAGE_UPLOAD_DIR = os.getenv(
        "RECORD_IMAGE_UPLOAD_DIR",
        str(BACKEND_DIR / "var" / "uploads" / "record-images"),
    )


class DevelopmentConfig(BaseConfig):
    APP_ENV = "development"
    DEV_FIXED_CODE = os.getenv("DEV_FIXED_CODE", "123456")


class TestingConfig(BaseConfig):
    APP_ENV = "testing"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    DEV_FIXED_CODE = "123456"
    TASK_IMAGE_UPLOAD_DIR = str(BACKEND_DIR / "var" / "testing-uploads" / "task-images")
    RECORD_IMAGE_UPLOAD_DIR = str(BACKEND_DIR / "var" / "testing-uploads" / "record-images")


class ProductionConfig(BaseConfig):
    APP_ENV = "production"
    DEV_FIXED_CODE = None


config_by_env = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
