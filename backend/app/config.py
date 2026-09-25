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

    validate_production_audio_config(config)
    validate_production_wechat_config(config)


def validate_production_audio_config(config):
    if config.get("APP_ENV") != "production":
        return

    def normalized(field_name):
        value = config.get(field_name)
        return value.strip() if isinstance(value, str) else ""

    tts_provider = normalized("TTS_PROVIDER").casefold()
    storage_provider = normalized("AUDIO_STORAGE_PROVIDER").casefold()
    if tts_provider != "edge":
        raise RuntimeError("Invalid production audio configuration: TTS_PROVIDER")
    if storage_provider != "r2":
        raise RuntimeError("Invalid production audio storage configuration: AUDIO_STORAGE_PROVIDER")

    for field_name in (
        "EDGE_TTS_BASE_URL",
        "R2_ACCOUNT_ID",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET",
    ):
        if not normalized(field_name):
            raise RuntimeError(f"Invalid production audio configuration: {field_name}")


def validate_production_wechat_config(config):
    if config.get("APP_ENV") != "production":
        return

    def normalized(field_name):
        value = config.get(field_name)
        return value.strip() if isinstance(value, str) else ""

    if normalized("AUTH_LOGIN_MODE").casefold() != "wechat_only":
        raise RuntimeError("Invalid production configuration: AUTH_LOGIN_MODE")

    for field_name in (
        "WECHAT_APP_ID",
        "WECHAT_APP_SECRET",
    ):
        value = normalized(field_name)
        if (
            not value
            or value.casefold() in _PRODUCTION_SECRET_PLACEHOLDERS
            or "replace" in value.casefold()
            or "changeme" in value.casefold()
        ):
            raise RuntimeError(f"Invalid production configuration: {field_name}")

    value = config.get("WECHAT_TIMEOUT_SECONDS")
    if not isinstance(value, int) or value < 1:
        raise RuntimeError("Invalid production configuration: WECHAT_TIMEOUT_SECONDS")


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
    GUIDE_AUDIO_WORKER_POLL_SECONDS = int(os.getenv("GUIDE_AUDIO_WORKER_POLL_SECONDS", "1"))
    GUIDE_AUDIO_MAX_ATTEMPTS = int(os.getenv("GUIDE_AUDIO_MAX_ATTEMPTS", "3"))
    GUIDE_AUDIO_LEASE_SECONDS = int(os.getenv("GUIDE_AUDIO_LEASE_SECONDS", "60"))
    TTS_PROVIDER = os.getenv("TTS_PROVIDER", "unconfigured")
    EDGE_TTS_BASE_URL = os.getenv("EDGE_TTS_BASE_URL", "")
    EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "zh-CN-XiaoxiaoNeural")
    EDGE_TTS_SPEED = float(os.getenv("EDGE_TTS_SPEED", "1.0"))
    EDGE_TTS_PITCH = os.getenv("EDGE_TTS_PITCH", "0")
    EDGE_TTS_STYLE = os.getenv("EDGE_TTS_STYLE", "general")
    EDGE_TTS_TIMEOUT_SECONDS = int(os.getenv("EDGE_TTS_TIMEOUT_SECONDS", "30"))
    AUDIO_STORAGE_PROVIDER = os.getenv("AUDIO_STORAGE_PROVIDER", "unconfigured")
    R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET = os.getenv("R2_BUCKET", "")
    AUDIO_SIGNED_URL_TTL_SECONDS = int(os.getenv("AUDIO_SIGNED_URL_TTL_SECONDS", "300"))
    AUTH_LOGIN_MODE = os.getenv("AUTH_LOGIN_MODE", "wechat_only")
    WECHAT_APP_ID = os.getenv("WECHAT_APP_ID", "")
    WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET", "")
    WECHAT_TIMEOUT_SECONDS = int(os.getenv("WECHAT_TIMEOUT_SECONDS", "10"))
    SMS_PROVIDER = os.getenv("SMS_PROVIDER", "unconfigured")
    SMS_HTTP_ENDPOINT = os.getenv("SMS_HTTP_ENDPOINT", "")
    SMS_HTTP_TOKEN = os.getenv("SMS_HTTP_TOKEN", "")
    SMS_TEMPLATE_ID = os.getenv("SMS_TEMPLATE_ID", "")
    SMS_TIMEOUT_SECONDS = int(os.getenv("SMS_TIMEOUT_SECONDS", "10"))
    SMS_VERIFICATION_SECRET = os.getenv("SMS_VERIFICATION_SECRET", "")
    SMS_CODE_TTL_SECONDS = int(os.getenv("SMS_CODE_TTL_SECONDS", "300"))
    SMS_SEND_COOLDOWN_SECONDS = int(os.getenv("SMS_SEND_COOLDOWN_SECONDS", "60"))
    SMS_MAX_VERIFY_ATTEMPTS = int(os.getenv("SMS_MAX_VERIFY_ATTEMPTS", "5"))


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
