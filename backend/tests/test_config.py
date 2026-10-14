import pytest

from app import create_app
from app.config import ProductionConfig


VALID_SECRET_KEY = "test-secret-key-for-production-config-0001"
VALID_JWT_SECRET_KEY = "test-jwt-secret-key-for-production-config-0002"
VALID_WECHAT_APP_ID = "wx-test-app-id"
VALID_WECHAT_APP_SECRET = "test-wechat-app-secret"


@pytest.fixture()
def valid_production_secrets(monkeypatch):
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", VALID_SECRET_KEY)
    monkeypatch.setattr(ProductionConfig, "JWT_SECRET_KEY", VALID_JWT_SECRET_KEY)
    for name, value in {
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "CORS_ORIGINS": ["https://app.example.test"],
        "TTS_PROVIDER": "edge",
        "EDGE_TTS_BASE_URL": "https://edge-worker.example.test",
        "EDGE_TTS_VOICE": "zh-CN-XiaoxiaoNeural",
        "EDGE_TTS_SPEED": 1.0,
        "EDGE_TTS_PITCH": "0",
        "EDGE_TTS_STYLE": "general",
        "EDGE_TTS_TIMEOUT_SECONDS": 30,
        "AUDIO_STORAGE_PROVIDER": "r2",
        "R2_ACCOUNT_ID": "account-id-123",
        "R2_ACCESS_KEY_ID": "access-key",
        "R2_SECRET_ACCESS_KEY": "secret-key",
        "R2_BUCKET": "test-private-audio-bucket",
        "AUTH_LOGIN_MODE": "wechat_only",
        "WECHAT_APP_ID": VALID_WECHAT_APP_ID,
        "WECHAT_APP_SECRET": VALID_WECHAT_APP_SECRET,
        "WECHAT_TIMEOUT_SECONDS": 10,
    }.items():
        monkeypatch.setattr(ProductionConfig, name, value, raising=False)


def test_create_app_uses_production_from_app_env(monkeypatch, valid_production_secrets):
    monkeypatch.setenv("APP_ENV", "production")

    app = create_app()

    assert app.config["APP_ENV"] == "production"
    assert app.config["DEV_FIXED_CODE"] is None


def test_create_app_rejects_missing_app_env(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)

    with pytest.raises(RuntimeError, match="APP_ENV is required"):
        create_app()


@pytest.mark.parametrize("invalid_value", ["", "   "])
def test_create_app_rejects_blank_app_env(monkeypatch, invalid_value):
    monkeypatch.setenv("APP_ENV", invalid_value)

    with pytest.raises(RuntimeError, match="APP_ENV is required"):
        create_app()


def test_create_app_rejects_unknown_app_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "prodction")

    with pytest.raises(RuntimeError, match="Invalid application environment"):
        create_app()


@pytest.mark.parametrize("field_name", ["SECRET_KEY", "JWT_SECRET_KEY"])
def test_production_rejects_missing_secret(field_name, monkeypatch, valid_production_secrets):
    monkeypatch.setattr(ProductionConfig, field_name, "")

    with pytest.raises(RuntimeError, match=field_name):
        create_app("production")


@pytest.mark.parametrize("invalid_value", ["replace-me", "changeme", "   "])
def test_production_rejects_placeholder_secret(invalid_value, monkeypatch, valid_production_secrets):
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", invalid_value)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app("production")


@pytest.mark.parametrize("field_name", ["SECRET_KEY", "JWT_SECRET_KEY"])
def test_production_rejects_short_secret(field_name, monkeypatch, valid_production_secrets):
    monkeypatch.setattr(ProductionConfig, field_name, "x" * 31)

    with pytest.raises(RuntimeError, match=field_name):
        create_app("production")


def test_production_accepts_valid_test_only_secrets(valid_production_secrets):
    app = create_app("production")

    assert app.config["APP_ENV"] == "production"
    assert app.config["DEV_FIXED_CODE"] is None


@pytest.mark.parametrize(
    "database_url",
    [
        "mysql+pymysql://username:password@db.example.test:3306/tonglvji",
        "mysql+pymysql://real-user:replace-me@db.example.test:3306/tonglvji",
        "mysql+pymysql://real-user:changeme@db.example.test:3306/tonglvji",
    ],
)
def test_production_rejects_placeholder_database_url(database_url, monkeypatch, valid_production_secrets):
    monkeypatch.setattr(ProductionConfig, "SQLALCHEMY_DATABASE_URI", database_url)

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        create_app("production")


def test_production_rejects_empty_database_url(monkeypatch, valid_production_secrets):
    monkeypatch.setattr(ProductionConfig, "SQLALCHEMY_DATABASE_URI", "")

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        create_app("production")


@pytest.mark.parametrize(
    "origins",
    [
        [],
        ["http://localhost:5173"],
        ["http://127.0.0.1:5173"],
        ["http://localhost:5174"],
        ["http://127.0.0.1:5174"],
    ],
)
def test_production_rejects_empty_or_development_cors_origins(origins, monkeypatch, valid_production_secrets):
    monkeypatch.setattr(ProductionConfig, "CORS_ORIGINS", origins)

    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        create_app("production")


@pytest.mark.parametrize(
    "field_name",
    [
        "EDGE_TTS_BASE_URL",
        "R2_ACCOUNT_ID",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET",
    ],
)
def test_production_rejects_missing_edge_or_r2_configuration(field_name, monkeypatch, valid_production_secrets):
    monkeypatch.setattr(ProductionConfig, field_name, "", raising=False)

    with pytest.raises(RuntimeError, match=field_name):
        create_app("production")


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("TTS_PROVIDER", "fake"),
        ("TTS_PROVIDER", "unconfigured"),
        ("AUDIO_STORAGE_PROVIDER", "fake"),
        ("AUDIO_STORAGE_PROVIDER", "unconfigured"),
    ],
)
def test_production_rejects_fake_or_unconfigured_audio_providers(
    field_name, invalid_value, monkeypatch, valid_production_secrets
):
    monkeypatch.setattr(ProductionConfig, field_name, invalid_value)

    with pytest.raises(RuntimeError, match=field_name):
        create_app("production")


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("WECHAT_APP_ID", ""),
        ("WECHAT_APP_SECRET", ""),
        ("WECHAT_APP_SECRET", "replace-with-real-secret"),
    ],
)
def test_production_rejects_missing_or_placeholder_wechat_configuration(
    field_name, invalid_value, monkeypatch, valid_production_secrets
):
    monkeypatch.setattr(ProductionConfig, field_name, invalid_value, raising=False)

    with pytest.raises(RuntimeError, match=field_name):
        create_app("production")


def test_production_does_not_require_legacy_sms_configuration(monkeypatch, valid_production_secrets):
    for field_name in (
        "SMS_PROVIDER",
        "SMS_HTTP_ENDPOINT",
        "SMS_HTTP_TOKEN",
        "SMS_TEMPLATE_ID",
        "SMS_VERIFICATION_SECRET",
    ):
        monkeypatch.setattr(ProductionConfig, field_name, "", raising=False)

    app = create_app("production")

    assert app.config["APP_ENV"] == "production"


def test_development_configuration_remains_available(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)

    app = create_app("development")

    assert app.config["APP_ENV"] == "development"


def test_testing_configuration_remains_available():
    app = create_app("testing")

    assert app.config["APP_ENV"] == "testing"
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
