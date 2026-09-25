from datetime import timedelta

import pytest
from sqlalchemy import event

from app import create_app
from app.config import ProductionConfig
from app.extensions import db
from app.models import PhoneVerificationCode, User
from app.services import auth as auth_service
from app.services.sms import SMSProviderError
from app.utils.time import utc_now


VALID_SECRET_KEY = "test-secret-key-for-production-phone-auth-0001"
VALID_JWT_SECRET_KEY = "test-jwt-secret-key-for-production-phone-auth-0002"
VALID_WECHAT_APP_ID = "wx-test-app-id"
VALID_WECHAT_APP_SECRET = "test-wechat-app-secret"
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
        "AUTH_LOGIN_MODE": "wechat_only",
        "WECHAT_APP_ID": VALID_WECHAT_APP_ID,
        "WECHAT_APP_SECRET": VALID_WECHAT_APP_SECRET,
        "WECHAT_TIMEOUT_SECONDS": 10,
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


def assert_feature_disabled(response):
    assert response.status_code == 403
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "FEATURE_DISABLED"


def create_legacy_otp_record(app, code, *, expires_at=None, failed_attempts=0):
    record = PhoneVerificationCode(
        phone=PHONE,
        code_hash=auth_service.verification_code_hash(PHONE, code, app.config),
        sent_at=utc_now(),
        expires_at=expires_at or utc_now() + timedelta(minutes=5),
        failed_attempts=failed_attempts,
        consumed_at=None,
    )
    db.session.add(record)
    db.session.commit()
    return record


def test_production_send_code_is_disabled_before_any_sms_provider_call_or_otp_write(production_app, monkeypatch):
    client, provider = client_and_provider(production_app)
    monkeypatch.setattr(
        auth_service,
        "generate_verification_code",
        lambda: pytest.fail("production must not generate a verification code"),
    )

    response = send_code(client)

    assert_feature_disabled(response)
    assert provider.calls == []
    assert db.session.get(PhoneVerificationCode, PHONE) is None


def test_production_send_code_stays_disabled_when_the_legacy_provider_is_unavailable(production_app):
    client, provider = client_and_provider(production_app)
    provider.error = SMSProviderError("provider unavailable")

    response = send_code(client)

    assert_feature_disabled(response)
    assert provider.calls == []


def test_production_disabled_send_code_response_never_contains_verification_code(production_app):
    client, _provider = client_and_provider(production_app)

    response = send_code(client)

    assert_feature_disabled(response)
    assert "123456" not in response.get_data(as_text=True)
    assert "code" not in response.get_json().get("data", {})


def test_production_phone_login_is_disabled_without_creating_user_or_returning_jwt(production_app):
    client, _provider = client_and_provider(production_app)

    response = login(client, "123456")

    assert_feature_disabled(response)
    assert User.query.filter_by(phone=PHONE).count() == 0
    assert "accessToken" not in response.get_json().get("data", {})


def test_production_phone_login_is_disabled_for_any_submitted_code(production_app):
    client, _provider = client_and_provider(production_app)

    response = login(client, "000000")

    assert_feature_disabled(response)


def test_legacy_otp_expired_code_is_rejected_and_consumed(production_app):
    app, _provider = production_app
    create_legacy_otp_record(app, "654321", expires_at=utc_now() - timedelta(seconds=1))

    with pytest.raises(auth_service.AuthError) as error:
        auth_service._verify_production_code(PHONE, "654321", app.config)

    assert error.value.code == "VERIFICATION_CODE_EXPIRED"
    assert db.session.get(PhoneVerificationCode, PHONE).consumed_at is not None


def test_legacy_otp_code_is_consumed_after_a_verified_login(production_app):
    app, _provider = production_app
    create_legacy_otp_record(app, "654321")
    verification_record = auth_service._verify_production_code(PHONE, "654321", app.config)
    auth_service._login_phone_user(PHONE, app.config, verification_record)

    assert db.session.get(PhoneVerificationCode, PHONE).consumed_at is not None


def test_legacy_otp_hash_rejects_a_code_replaced_by_a_later_record(production_app):
    app, _provider = production_app
    record = create_legacy_otp_record(app, "222222")

    with pytest.raises(auth_service.AuthError) as error:
        auth_service._verify_production_code(PHONE, "111111", app.config)

    assert error.value.code == "INVALID_VERIFICATION_CODE"
    assert db.session.get(PhoneVerificationCode, PHONE).code_hash == record.code_hash
    assert db.session.get(PhoneVerificationCode, PHONE).code_hash != "222222"


def test_legacy_otp_record_retains_sent_expiry_attempt_and_consumption_lifecycle_fields(production_app):
    app, _provider = production_app
    record = create_legacy_otp_record(app, "654321")

    assert record.code_hash != "654321"
    assert record.sent_at < record.expires_at
    assert record.failed_attempts == 0
    assert record.consumed_at is None


def test_legacy_otp_failed_attempt_limit_locks_the_code(production_app):
    app, _provider = production_app
    app.config["SMS_MAX_VERIFY_ATTEMPTS"] = 2
    create_legacy_otp_record(app, "654321", failed_attempts=1)

    with pytest.raises(auth_service.AuthError) as error:
        auth_service._verify_production_code(PHONE, "000000", app.config)

    assert error.value.code == "VERIFICATION_CODE_ATTEMPTS_EXCEEDED"
    record = db.session.get(PhoneVerificationCode, PHONE)
    assert record.failed_attempts == 2
    assert record.consumed_at is not None


def test_development_and_testing_keep_the_controlled_fixed_code_contract(testing_app):
    client = testing_app.test_client()

    assert send_code(client).status_code == 200
    response = login(client, testing_app.config["DEV_FIXED_CODE"])

    assert response.status_code == 200
    assert response.get_json()["data"]["user"]["phone"] == PHONE


def test_production_disables_the_fixed_development_code_path(production_app):
    client, _provider = client_and_provider(production_app)

    response = login(client, "123456")

    assert_feature_disabled(response)


def test_production_ignores_an_accidentally_configured_dev_fixed_code(production_app):
    app, _provider = production_app
    app.config["DEV_FIXED_CODE"] = "123456"

    response = login(app.test_client(), "123456")

    assert_feature_disabled(response)


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
