from datetime import timedelta

import pytest
from sqlalchemy import event

from app import create_app
from app.config import ProductionConfig
from app.extensions import db
from app.models import User
from app.services import auth as auth_service
from app.services.sms import SMSProviderError
from app.utils.time import utc_now


VALID_SECRET_KEY = "test-secret-key-for-production-phone-auth-0001"
VALID_JWT_SECRET_KEY = "test-jwt-secret-key-for-production-phone-auth-0002"
VALID_SMS_VERIFICATION_SECRET = "test-sms-verification-secret-for-production-0003"
PHONE = "13800138000"


class RecordingSMSProvider:
    def __init__(self):
        self.calls = []
        self.error = None

    def send_verification_code(self, phone, code):
        if self.error:
            raise self.error
        self.calls.append((phone, code))


@pytest.fixture()
def sqlite_user_ids():
    next_id = 5000

    @event.listens_for(User, "before_insert")
    def assign_user_id(_mapper, _connection, target):
        nonlocal next_id
        if target.id is None:
            target.id = next_id
            next_id += 1

    yield
    event.remove(User, "before_insert", assign_user_id)


def configure_production(monkeypatch):
    for name, value in {
        "SECRET_KEY": VALID_SECRET_KEY,
        "JWT_SECRET_KEY": VALID_JWT_SECRET_KEY,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
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
        "SMS_PROVIDER": "http",
        "SMS_HTTP_ENDPOINT": "https://sms.example.test/send",
        "SMS_HTTP_TOKEN": "test-sms-http-token",
        "SMS_TEMPLATE_ID": "tonglvji-login",
        "SMS_VERIFICATION_SECRET": VALID_SMS_VERIFICATION_SECRET,
        "SMS_CODE_TTL_SECONDS": 300,
        "SMS_SEND_COOLDOWN_SECONDS": 60,
        "SMS_MAX_VERIFY_ATTEMPTS": 5,
    }.items():
        monkeypatch.setattr(ProductionConfig, name, value, raising=False)


@pytest.fixture()
def production_app(monkeypatch, sqlite_user_ids):
    configure_production(monkeypatch)
    provider = RecordingSMSProvider()
    monkeypatch.setattr(auth_service, "get_sms_provider", lambda _config: provider, raising=False)
    app = create_app("production")
    with app.app_context():
        db.create_all()
        yield app, provider
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def testing_app(sqlite_user_ids):
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def client_and_provider(production_app):
    app, provider = production_app
    return app.test_client(), provider


def send_code(client, phone=PHONE):
    return client.post("/api/v1/auth/send-code", json={"phone": phone})


def login(client, code, phone=PHONE):
    return client.post("/api/v1/auth/login", json={"phone": phone, "code": code})


def set_generated_code(monkeypatch, *codes):
    values = iter(codes)
    monkeypatch.setattr(
        auth_service,
        "generate_verification_code",
        lambda: next(values),
        raising=False,
    )


def test_production_send_code_uses_configured_provider_without_returning_code(production_app, monkeypatch):
    client, provider = client_and_provider(production_app)
    set_generated_code(monkeypatch, "654321")

    response = send_code(client)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"] == {"cooldownSeconds": 60}
    assert "code" not in payload["data"]
    assert provider.calls == [(PHONE, "654321")]


def test_production_provider_failure_is_not_reported_as_sent(production_app, monkeypatch):
    client, provider = client_and_provider(production_app)
    provider.error = SMSProviderError("provider unavailable")
    set_generated_code(monkeypatch, "654321")

    response = send_code(client)

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "SMS_PROVIDER_UNAVAILABLE"
    assert provider.calls == []


def test_production_send_code_response_never_contains_verification_code(production_app, monkeypatch):
    client, _provider = client_and_provider(production_app)
    set_generated_code(monkeypatch, "654321")

    response = send_code(client)

    assert response.status_code == 200
    assert "654321" not in response.get_data(as_text=True)
    assert "code" not in response.get_json()["data"]


def test_production_correct_code_creates_session_user_and_jwt(production_app, monkeypatch):
    client, _provider = client_and_provider(production_app)
    set_generated_code(monkeypatch, "654321")
    assert send_code(client).status_code == 200

    response = login(client, "654321")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["accessToken"]
    assert payload["user"]["phone"] == PHONE


def test_production_wrong_code_is_rejected_after_a_real_send(production_app, monkeypatch):
    client, _provider = client_and_provider(production_app)
    set_generated_code(monkeypatch, "654321")
    assert send_code(client).status_code == 200

    response = login(client, "000000")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "INVALID_VERIFICATION_CODE"


def test_production_expired_code_is_rejected(production_app, monkeypatch):
    app, _provider = production_app
    client = app.test_client()
    set_generated_code(monkeypatch, "654321")
    assert send_code(client).status_code == 200

    from app.models import PhoneVerificationCode

    with app.app_context():
        record = db.session.get(PhoneVerificationCode, PHONE)
        record.expires_at = utc_now() - timedelta(seconds=1)
        db.session.commit()

    response = login(client, "654321")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "VERIFICATION_CODE_EXPIRED"


def test_production_code_is_consumed_after_success(production_app, monkeypatch):
    client, _provider = client_and_provider(production_app)
    set_generated_code(monkeypatch, "654321")
    assert send_code(client).status_code == 200
    assert login(client, "654321").status_code == 200

    response = login(client, "654321")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "INVALID_VERIFICATION_CODE"


def test_resend_invalidates_the_previous_code(production_app, monkeypatch):
    app, _provider = production_app
    client = app.test_client()
    set_generated_code(monkeypatch, "111111", "222222")
    assert send_code(client).status_code == 200

    from app.models import PhoneVerificationCode

    with app.app_context():
        record = db.session.get(PhoneVerificationCode, PHONE)
        record.sent_at = utc_now() - timedelta(seconds=61)
        db.session.commit()

    assert send_code(client).status_code == 200
    assert login(client, "111111").status_code == 401
    assert login(client, "222222").status_code == 200


def test_production_send_cooldown_is_enforced(production_app, monkeypatch):
    client, _provider = client_and_provider(production_app)
    set_generated_code(monkeypatch, "654321", "123456")
    assert send_code(client).status_code == 200

    response = send_code(client)

    assert response.status_code == 429
    assert response.get_json()["error"]["code"] == "SMS_COOLDOWN"


def test_production_failed_attempt_limit_locks_the_code(production_app, monkeypatch):
    app, _provider = production_app
    app.config["SMS_MAX_VERIFY_ATTEMPTS"] = 2
    client = app.test_client()
    set_generated_code(monkeypatch, "654321")
    assert send_code(client).status_code == 200
    assert login(client, "000000").status_code == 401

    response = login(client, "000000")

    assert response.status_code == 429
    assert response.get_json()["error"]["code"] == "VERIFICATION_CODE_ATTEMPTS_EXCEEDED"
    assert login(client, "654321").status_code == 401


def test_development_and_testing_keep_the_controlled_fixed_code_contract(testing_app):
    client = testing_app.test_client()

    assert send_code(client).status_code == 200
    response = login(client, testing_app.config["DEV_FIXED_CODE"])

    assert response.status_code == 200
    assert response.get_json()["data"]["user"]["phone"] == PHONE


def test_production_never_accepts_dev_fixed_code(production_app):
    client, _provider = client_and_provider(production_app)

    response = login(client, "123456")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "INVALID_VERIFICATION_CODE"


def test_production_ignores_an_accidentally_configured_dev_fixed_code(production_app):
    app, _provider = production_app
    app.config["DEV_FIXED_CODE"] = "123456"

    response = login(app.test_client(), "123456")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "INVALID_VERIFICATION_CODE"


def test_mock_wechat_remains_disabled_in_production(production_app):
    client, _provider = client_and_provider(production_app)

    response = client.post("/api/v1/auth/mock-wechat-login", json={"mockCode": "test-code"})

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "FEATURE_DISABLED"


def test_mock_wechat_remains_available_for_testing(testing_app):
    response = testing_app.test_client().post(
        "/api/v1/auth/mock-wechat-login",
        json={"mockCode": "test-code"},
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["accessToken"]
