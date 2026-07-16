import pytest
from datetime import timedelta
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User


@pytest.fixture()
def auth_db(app):
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def test_send_code_requires_phone(client):
    response = client.post("/api/v1/auth/send-code", json={})

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "VALIDATION_ERROR"


def test_send_code_rejects_invalid_phone(client):
    response = client.post("/api/v1/auth/send-code", json={"phone": "123"})

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_PHONE"


def test_send_code_success_does_not_return_code(client):
    response = client.post("/api/v1/auth/send-code", json={"phone": "13800138000"})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["message"] == "Verification code sent"
    assert payload["data"] == {"cooldownSeconds": 60}
    assert "code" not in payload["data"]


def test_login_rejects_wrong_code(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"phone": "13800138000", "code": "000000"},
    )

    assert response.status_code == 401
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_VERIFICATION_CODE"


def test_login_success_returns_access_token_and_user(client, monkeypatch):
    def fake_login(payload, config):
        return {
            "accessToken": "test-token",
            "tokenType": "Bearer",
            "expiresInHours": 168,
            "user": {
                "id": 1001,
                "phone": payload["phone"],
                "nickname": "童旅用户",
                "city": None,
            },
        }

    monkeypatch.setattr("app.api.v1.auth.login_with_phone", fake_login)

    response = client.post(
        "/api/v1/auth/login",
        json={"phone": "13800138000", "code": "123456"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["accessToken"]
    assert payload["data"]["tokenType"] == "Bearer"
    assert payload["data"]["expiresInHours"] == 168
    assert payload["data"]["user"]["phone"] == "13800138000"
    assert payload["data"]["user"]["nickname"] == "童旅用户"
    assert set(payload["data"]["user"]) == {"id", "phone", "nickname", "city"}


def test_auth_me_without_token_returns_json(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "UNAUTHORIZED"


def test_auth_me_with_valid_jwt_returns_user(client, app, auth_db):
    with app.app_context():
        user = User(id=1001, phone="13800138001", nickname="童旅用户")
        db.session.add(user)
        db.session.commit()
        token = create_access_token(identity=str(user.id))

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["user"] == {
        "id": 1001,
        "phone": "13800138001",
        "nickname": "童旅用户",
        "city": None,
    }


def test_invalid_token_returns_json(client):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})

    assert response.status_code == 401
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_TOKEN"


def test_expired_token_returns_json(client, app, auth_db):
    with app.app_context():
        user = User(id=1002, phone="13800138002", nickname="童旅用户")
        db.session.add(user)
        db.session.commit()
        token = create_access_token(identity=str(user.id), expires_delta=timedelta(seconds=-1))

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "TOKEN_EXPIRED"


def test_mock_wechat_login_disabled_in_production():
    from app import create_app

    app = create_app("production")
    response = app.test_client().post("/api/v1/auth/mock-wechat-login", json={})

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "FEATURE_DISABLED"


def test_logout_without_token_is_rejected(client):
    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 401
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "UNAUTHORIZED"
