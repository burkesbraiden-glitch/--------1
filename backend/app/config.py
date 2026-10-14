from datetime import timedelta
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from PIL import features


BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


def _split_origins(value):
    return [origin.strip() for origin in value.split(",") if origin.strip()]


_PRODUCTION_SECRET_FIELDS = ("SECRET_KEY", "JWT_SECRET_KEY")
_PRODUCTION_SECRET_PLACEHOLDERS = {"replace-me", "changeme"}
_MINIMUM_PRODUCTION_SECRET_LENGTH = 32
_PRODUCTION_DATABASE_URL_PLACEHOLDER_TOKENS = ("username", "password", "replace-me", "changeme")
_PRODUCTION_RATE_LIMIT_STORAGE_PLACEHOLDER_TOKENS = (
    "username",
    "password",
    "replace-me",
    "changeme",
    "placeholder",
)
_DEVELOPMENT_CORS_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
}


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

    validate_production_database_config(config)
    validate_production_cors_config(config)
    validate_production_rate_limit_config(config)
    validate_production_request_body_config(config)
    validate_production_image_config(config)
    validate_production_audio_config(config)
    validate_production_wechat_config(config)


def validate_production_database_config(config):
    if config.get("APP_ENV") != "production":
        return

    database_url = config.get("SQLALCHEMY_DATABASE_URI")
    normalized_url = database_url.strip() if isinstance(database_url, str) else ""
    if (
        not normalized_url
        or any(token in normalized_url.casefold() for token in _PRODUCTION_DATABASE_URL_PLACEHOLDER_TOKENS)
    ):
        raise RuntimeError("Invalid production configuration: DATABASE_URL")


def validate_production_cors_config(config):
    if config.get("APP_ENV") != "production":
        return

    origins = config.get("CORS_ORIGINS")
    if not isinstance(origins, (list, tuple)) or not origins:
        raise RuntimeError("Invalid production configuration: CORS_ORIGINS")

    for origin in origins:
        normalized_origin = origin.strip() if isinstance(origin, str) else ""
        parsed_origin = urlparse(normalized_origin)
        if (
            not normalized_origin
            or normalized_origin.casefold() in _DEVELOPMENT_CORS_ORIGINS
            or parsed_origin.scheme != "https"
            or not parsed_origin.netloc
        ):
            raise RuntimeError("Invalid production configuration: CORS_ORIGINS")


def validate_production_rate_limit_config(config):
    if config.get("APP_ENV") != "production":
        return

    storage_uri = config.get("RATELIMIT_STORAGE_URI")
    normalized_uri = storage_uri.strip() if isinstance(storage_uri, str) else ""
    parsed_uri = urlparse(normalized_uri)
    hostname = parsed_uri.hostname.casefold() if parsed_uri.hostname else ""
    if (
        not normalized_uri
        or parsed_uri.scheme not in {"redis", "rediss"}
        or not hostname
        or hostname in {"localhost", "127.0.0.1", "::1"}
        or any(token in normalized_uri.casefold() for token in _PRODUCTION_RATE_LIMIT_STORAGE_PLACEHOLDER_TOKENS)
    ):
        raise RuntimeError("Invalid production configuration: RATELIMIT_STORAGE_URI")


def validate_production_request_body_config(config):
    if config.get("APP_ENV") != "production":
        return

    max_content_length = config.get("MAX_CONTENT_LENGTH")
    task_image_max_bytes = config.get("TASK_IMAGE_MAX_BYTES")
    if (
        not isinstance(max_content_length, int)
        or isinstance(max_content_length, bool)
        or not isinstance(task_image_max_bytes, int)
        or isinstance(task_image_max_bytes, bool)
        or max_content_length <= 0
        or task_image_max_bytes <= 0
        or max_content_length <= task_image_max_bytes
    ):
        raise RuntimeError("Invalid production configuration: MAX_CONTENT_LENGTH")


def validate_production_image_config(config):
    if config.get("APP_ENV") != "production":
        return

    max_pixels = config.get("TASK_IMAGE_MAX_PIXELS")
    jpeg_quality = config.get("TASK_IMAGE_JPEG_QUALITY")
    if not isinstance(max_pixels, int) or isinstance(max_pixels, bool) or max_pixels <= 0:
        raise RuntimeError("Invalid production configuration: TASK_IMAGE_MAX_PIXELS")
    if (
        not isinstance(jpeg_quality, int)
        or isinstance(jpeg_quality, bool)
        or not 1 <= jpeg_quality <= 95
    ):
        raise RuntimeError("Invalid production configuration: TASK_IMAGE_JPEG_QUALITY")
    if not features.check("webp"):
        raise RuntimeError("Invalid production image configuration: WebP support")


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
    APP_ENV = os.getenv("APP_ENV")
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
    TASK_IMAGE_MAX_PIXELS = int(os.getenv("TASK_IMAGE_MAX_PIXELS", "25000000"))
    TASK_IMAGE_JPEG_QUALITY = int(os.getenv("TASK_IMAGE_JPEG_QUALITY", "90"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(12 * 1024 * 1024)))
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_ENABLED = True
    RATELIMIT_HEADERS_ENABLED = True
    RATE_LIMIT_SEND_CODE = os.getenv("RATE_LIMIT_SEND_CODE", "5 per minute")
    RATE_LIMIT_LOGIN = os.getenv("RATE_LIMIT_LOGIN", "10 per minute")
    RATE_LIMIT_WECHAT_LOGIN = os.getenv("RATE_LIMIT_WECHAT_LOGIN", "10 per minute")
    RATE_LIMIT_MOCK_WECHAT_LOGIN = os.getenv("RATE_LIMIT_MOCK_WECHAT_LOGIN", "30 per minute")
    RATE_LIMIT_GENERATION = os.getenv("RATE_LIMIT_GENERATION", "12 per hour")
    RATE_LIMIT_AUDIO = os.getenv("RATE_LIMIT_AUDIO", "12 per hour")
    RATE_LIMIT_UPLOAD = os.getenv("RATE_LIMIT_UPLOAD", "30 per hour")
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
    RATELIMIT_STORAGE_URI = "memory://"


class TestingConfig(BaseConfig):
    APP_ENV = "testing"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    DEV_FIXED_CODE = "123456"
    TASK_IMAGE_UPLOAD_DIR = str(BACKEND_DIR / "var" / "testing-uploads" / "task-images")
    RECORD_IMAGE_UPLOAD_DIR = str(BACKEND_DIR / "var" / "testing-uploads" / "record-images")
    RATELIMIT_STORAGE_URI = "memory://"


class ProductionConfig(BaseConfig):
    APP_ENV = "production"
    DEV_FIXED_CODE = None
    CORS_ORIGINS = _split_origins(os.getenv("CORS_ORIGINS", ""))


config_by_env = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
