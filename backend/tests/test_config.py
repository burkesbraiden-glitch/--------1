import pytest

from app import create_app
from app.config import ProductionConfig


VALID_SECRET_KEY = "test-secret-key-for-production-config-0001"
VALID_JWT_SECRET_KEY = "test-jwt-secret-key-for-production-config-0002"


@pytest.fixture()
def valid_production_secrets(monkeypatch):
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", VALID_SECRET_KEY)
    monkeypatch.setattr(ProductionConfig, "JWT_SECRET_KEY", VALID_JWT_SECRET_KEY)


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


def test_development_configuration_remains_available(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)

    app = create_app("development")

    assert app.config["APP_ENV"] == "development"


def test_testing_configuration_remains_available():
    app = create_app("testing")

    assert app.config["APP_ENV"] == "testing"
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
