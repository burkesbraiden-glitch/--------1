import pytest

from app import create_app
from app.config import ProductionConfig


VALID_SECRET_KEY = "test-secret-key-for-production-config-0001"
VALID_JWT_SECRET_KEY = "test-jwt-secret-key-for-production-config-0002"


@pytest.fixture()
def valid_production_secrets(monkeypatch):
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", VALID_SECRET_KEY)
    monkeypatch.setattr(ProductionConfig, "JWT_SECRET_KEY", VALID_JWT_SECRET_KEY)
    for name, value in {
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
    }.items():
        monkeypatch.setattr(ProductionConfig, name, value, raising=False)


def test_create_app_uses_production_from_app_env(monkeypatch, valid_production_secrets):
    monkeypatch.setenv("APP_ENV", "production")

    app = create_app()

    assert app.config["APP_ENV"] == "production"
    assert app.config["DEV_FIXED_CODE"] is None


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


def test_development_configuration_remains_available(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)

    app = create_app("development")

    assert app.config["APP_ENV"] == "development"


def test_testing_configuration_remains_available():
    app = create_app("testing")

    assert app.config["APP_ENV"] == "testing"
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
