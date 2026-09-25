from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import event

from app import create_app
from app.config import ProductionConfig
from app.extensions import db
from app.models import User
from app.services.wechat import WechatAuthProvider, WechatProviderResponseError


VALID_SECRET_KEY = "test-secret-key-for-production-config-0001"
VALID_JWT_SECRET_KEY = "test-jwt-secret-key-for-production-config-0002"
VALID_WECHAT_APP_ID = "wx-test-app-id"
VALID_WECHAT_APP_SECRET = "test-wechat-app-secret"


class FakeWechatProvider:
    def __init__(self, identity=None, error=None):
        self.identity = identity
        self.error = error

    def exchange_code(self, code):
        if self.error:
            raise self.error
        return self.identity


@pytest.fixture()
def production_app(monkeypatch):
    for name, value in {
        "SECRET_KEY": VALID_SECRET_KEY,
        "JWT_SECRET_KEY": VALID_JWT_SECRET_KEY,
        "TTS_PROVIDER": "edge",
        "EDGE_TTS_BASE_URL": "https://edge-worker.example.test",
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
        "SMS_VERIFICATION_SECRET": "test-sms-verification-secret-for-auth-0003",
    }.items():
        monkeypatch.setattr(ProductionConfig, name, value, raising=False)

    app = create_app("production")
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite:///:memory:", TESTING=True)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(production_app):
    return production_app.test_client()


@pytest.fixture()
def sqlite_user_ids():
    next_id = {"value": 10000}

    def assign_sqlite_user_id(mapper, connection, target):
        if target.id is None:
            next_id["value"] += 1
            target.id = next_id["value"]

    event.listen(User, "before_insert", assign_sqlite_user_id)
    try:
        yield
    finally:
        event.remove(User, "before_insert", assign_sqlite_user_id)


def fake_identity(*, openid="openid-first", unionid=None):
    return SimpleNamespace(openid=openid, unionid=unionid)


def install_provider(monkeypatch, provider):
    monkeypatch.setattr("app.services.auth.get_wechat_auth_provider", lambda config: provider)


def response_data(response):
    payload = response.get_json()
    assert payload["success"] is True
    return payload["data"]


def error_code(response):
    payload = response.get_json()
    assert payload["success"] is False
    return payload["error"]["code"]


def test_wechat_login_requires_a_code(client):
    response = client.post("/api/v1/auth/wechat-login", json={})

    assert response.status_code == 400
    assert error_code(response) == "VALIDATION_ERROR"


def test_wechat_login_rejects_invalid_provider_code(client, monkeypatch):
    install_provider(monkeypatch, FakeWechatProvider(error=Exception("invalid code")))

    response = client.post("/api/v1/auth/wechat-login", json={"code": "expired-code"})

    assert response.status_code == 401
    assert error_code(response) == "WECHAT_AUTHORIZATION_FAILED"


def test_wechat_login_maps_provider_timeout_to_safe_error(client, monkeypatch):
    install_provider(monkeypatch, FakeWechatProvider(error=TimeoutError("provider timeout")))

    response = client.post("/api/v1/auth/wechat-login", json={"code": "temporary-code"})

    assert response.status_code == 503
    assert error_code(response) == "WECHAT_PROVIDER_UNAVAILABLE"
    assert "timeout" not in response.get_data(as_text=True).casefold()


def test_wechat_login_rejects_a_provider_response_without_openid(client, monkeypatch):
    install_provider(monkeypatch, FakeWechatProvider(identity=SimpleNamespace(openid="", unionid=None)))

    response = client.post("/api/v1/auth/wechat-login", json={"code": "temporary-code"})

    assert response.status_code == 502
    assert error_code(response) == "WECHAT_PROVIDER_RESPONSE_INVALID"


class FakeWechatHTTPResponse:
    status = 200

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def getcode(self):
        return self.status

    def read(self, _limit):
        return self.body


def test_provider_rejects_malformed_json_without_exposing_provider_body():
    provider = WechatAuthProvider(
        app_id=VALID_WECHAT_APP_ID,
        app_secret=VALID_WECHAT_APP_SECRET,
        timeout_seconds=10,
        opener=lambda _request, timeout: FakeWechatHTTPResponse(b"not-json"),
    )

    with pytest.raises(WechatProviderResponseError):
        provider.exchange_code("temporary-code")


def test_provider_returns_identity_only_and_does_not_serialize_wechat_tokens():
    captured_request = {}

    def opener(request, timeout):
        captured_request["query"] = parse_qs(urlparse(request.full_url).query)
        assert timeout == 10
        return FakeWechatHTTPResponse(
            b'{"access_token":"provider-token","refresh_token":"provider-refresh","openid":"openid-safe","unionid":"union-safe"}'
        )

    identity = WechatAuthProvider(
        app_id=VALID_WECHAT_APP_ID,
        app_secret=VALID_WECHAT_APP_SECRET,
        timeout_seconds=10,
        opener=opener,
    ).exchange_code("temporary-code")

    assert captured_request["query"]["grant_type"] == ["authorization_code"]
    assert identity.openid == "openid-safe"
    assert identity.unionid == "union-safe"
    assert set(identity.__dict__) == {"openid", "unionid"}
    assert "access_token" not in identity.__dict__
    assert "refresh_token" not in identity.__dict__


def test_first_wechat_login_creates_phone_free_user_without_fake_profile_data(client, monkeypatch, sqlite_user_ids):
    install_provider(monkeypatch, FakeWechatProvider(identity=fake_identity(openid="openid-new", unionid="union-new")))

    response = client.post("/api/v1/auth/wechat-login", json={"code": "first-code"})

    data = response_data(response)
    assert data["accessToken"]
    assert data["user"] == {
        "id": data["user"]["id"],
        "phone": None,
        "nickname": None,
        "city": None,
    }
    user = db.session.get(User, data["user"]["id"])
    assert user.wechat_openid == "openid-new"
    assert user.wechat_unionid == "union-new"


def test_repeated_wechat_login_reuses_the_same_user(client, monkeypatch, sqlite_user_ids):
    provider = FakeWechatProvider(identity=fake_identity(openid="openid-repeat", unionid="union-repeat"))
    install_provider(monkeypatch, provider)

    first = response_data(client.post("/api/v1/auth/wechat-login", json={"code": "first-code"}))
    second = response_data(client.post("/api/v1/auth/wechat-login", json={"code": "second-code"}))

    assert second["user"]["id"] == first["user"]["id"]
    assert User.query.filter_by(wechat_openid="openid-repeat").count() == 1


def test_unionid_takes_precedence_over_openid_for_identity_matching(client, monkeypatch, sqlite_user_ids):
    user = User(id=20001, wechat_openid="openid-old", wechat_unionid="union-shared", nickname=None)
    db.session.add(user)
    db.session.commit()
    install_provider(monkeypatch, FakeWechatProvider(identity=fake_identity(openid="openid-new", unionid="union-shared")))

    data = response_data(client.post("/api/v1/auth/wechat-login", json={"code": "new-platform-code"}))

    assert data["user"]["id"] == user.id
    assert User.query.filter_by(wechat_unionid="union-shared").count() == 1


def test_unionid_has_a_unique_index_for_first_login_race_protection():
    column = User.__table__.c.wechat_unionid

    assert column.unique is True
    assert column.index is True


def test_wechat_login_keeps_jwt_and_auth_me_contract(client, monkeypatch, sqlite_user_ids):
    install_provider(monkeypatch, FakeWechatProvider(identity=fake_identity()))
    data = response_data(client.post("/api/v1/auth/wechat-login", json={"code": "me-code"}))

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {data['accessToken']}"})

    assert response.status_code == 200
    assert response_data(response)["user"] == data["user"]


def test_production_disables_both_phone_auth_endpoints(client):
    send_response = client.post("/api/v1/auth/send-code", json={"phone": "13800138000"})
    login_response = client.post("/api/v1/auth/login", json={"phone": "13800138000", "code": "123456"})

    assert send_response.status_code == 403
    assert error_code(send_response) == "FEATURE_DISABLED"
    assert login_response.status_code == 403
    assert error_code(login_response) == "FEATURE_DISABLED"


def test_production_keeps_mock_wechat_disabled(client):
    response = client.post("/api/v1/auth/mock-wechat-login", json={"mockCode": "test-only"})

    assert response.status_code == 403
    assert error_code(response) == "FEATURE_DISABLED"


def test_production_configuration_requires_wechat_but_not_sms(monkeypatch):
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", VALID_SECRET_KEY)
    monkeypatch.setattr(ProductionConfig, "JWT_SECRET_KEY", VALID_JWT_SECRET_KEY)
    monkeypatch.setattr(ProductionConfig, "TTS_PROVIDER", "edge")
    monkeypatch.setattr(ProductionConfig, "EDGE_TTS_BASE_URL", "https://edge-worker.example.test")
    monkeypatch.setattr(ProductionConfig, "AUDIO_STORAGE_PROVIDER", "r2")
    monkeypatch.setattr(ProductionConfig, "R2_ACCOUNT_ID", "account-id-123")
    monkeypatch.setattr(ProductionConfig, "R2_ACCESS_KEY_ID", "access-key")
    monkeypatch.setattr(ProductionConfig, "R2_SECRET_ACCESS_KEY", "secret-key")
    monkeypatch.setattr(ProductionConfig, "R2_BUCKET", "test-private-audio-bucket")
    monkeypatch.setattr(ProductionConfig, "AUTH_LOGIN_MODE", "wechat_only", raising=False)
    monkeypatch.setattr(ProductionConfig, "WECHAT_APP_ID", VALID_WECHAT_APP_ID, raising=False)
    monkeypatch.setattr(ProductionConfig, "WECHAT_APP_SECRET", VALID_WECHAT_APP_SECRET, raising=False)
    monkeypatch.setattr(ProductionConfig, "WECHAT_TIMEOUT_SECONDS", 10, raising=False)
    monkeypatch.setattr(ProductionConfig, "SMS_PROVIDER", "unconfigured")
    monkeypatch.setattr(ProductionConfig, "SMS_HTTP_ENDPOINT", "")
    monkeypatch.setattr(ProductionConfig, "SMS_HTTP_TOKEN", "")
    monkeypatch.setattr(ProductionConfig, "SMS_TEMPLATE_ID", "")
    monkeypatch.setattr(ProductionConfig, "SMS_VERIFICATION_SECRET", "")

    app = create_app("production")

    assert app.config["APP_ENV"] == "production"


@pytest.mark.parametrize("field_name", ["WECHAT_APP_ID", "WECHAT_APP_SECRET"])
def test_production_configuration_rejects_missing_wechat_credentials(monkeypatch, field_name):
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", VALID_SECRET_KEY)
    monkeypatch.setattr(ProductionConfig, "JWT_SECRET_KEY", VALID_JWT_SECRET_KEY)
    monkeypatch.setattr(ProductionConfig, "TTS_PROVIDER", "edge")
    monkeypatch.setattr(ProductionConfig, "EDGE_TTS_BASE_URL", "https://edge-worker.example.test")
    monkeypatch.setattr(ProductionConfig, "AUDIO_STORAGE_PROVIDER", "r2")
    monkeypatch.setattr(ProductionConfig, "R2_ACCOUNT_ID", "account-id-123")
    monkeypatch.setattr(ProductionConfig, "R2_ACCESS_KEY_ID", "access-key")
    monkeypatch.setattr(ProductionConfig, "R2_SECRET_ACCESS_KEY", "secret-key")
    monkeypatch.setattr(ProductionConfig, "R2_BUCKET", "test-private-audio-bucket")
    monkeypatch.setattr(ProductionConfig, "AUTH_LOGIN_MODE", "wechat_only", raising=False)
    monkeypatch.setattr(ProductionConfig, "WECHAT_APP_ID", VALID_WECHAT_APP_ID, raising=False)
    monkeypatch.setattr(ProductionConfig, "WECHAT_APP_SECRET", VALID_WECHAT_APP_SECRET, raising=False)
    monkeypatch.setattr(ProductionConfig, field_name, "", raising=False)

    with pytest.raises(RuntimeError, match=field_name):
        create_app("production")
