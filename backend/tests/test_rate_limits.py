import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.extensions import db, limiter
from app.models import Child, ExplorationPlan, User


@pytest.fixture()
def rate_limited_app():
    app = create_app("testing")
    with app.app_context():
        limiter.reset()
    yield app
    with app.app_context():
        limiter.reset()


@pytest.fixture()
def rate_limit_db(rate_limited_app):
    with rate_limited_app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def auth_headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def create_expensive_endpoint_fixture(app):
    with app.app_context():
        db.session.add_all(
            [
                User(id=1, phone="13800138000", nickname="限流用户一"),
                User(id=2, phone="13800138001", nickname="限流用户二"),
                Child(
                    id=10,
                    user_id=1,
                    name="小小探索家",
                    age=7,
                    age_group="7-12",
                    interests=[],
                    is_default=True,
                ),
                ExplorationPlan(
                    id=100,
                    user_id=1,
                    child_id=10,
                    title="故宫亲子探索",
                    destination="故宫博物院",
                    age_group="7-12",
                    duration="3小时",
                    interests=["历史故事"],
                    status="ready",
                ),
            ]
        )
        db.session.commit()


def assert_rate_limited(response):
    assert response.status_code == 429
    assert response.get_json() == {
        "success": False,
        "error": {
            "code": "RATE_LIMITED",
            "message": "Too many requests",
            "details": {},
        },
    }
    assert response.headers.get("Retry-After")
    assert response.headers.get("X-RateLimit-Limit")


def configured_limit_count(app, config_name):
    return int(app.config[config_name].split(maxsplit=1)[0])


def test_public_auth_limit_uses_remote_ip_and_returns_uniform_json(rate_limited_app):
    client = rate_limited_app.test_client()
    first_ip = {"REMOTE_ADDR": "198.51.100.10"}
    second_ip = {"REMOTE_ADDR": "198.51.100.11"}

    responses = [
        client.post("/api/v1/auth/send-code", json={}, environ_overrides=first_ip)
        for _ in range(configured_limit_count(rate_limited_app, "RATE_LIMIT_SEND_CODE"))
    ]
    blocked = client.post("/api/v1/auth/send-code", json={}, environ_overrides=first_ip)
    other_client = client.post("/api/v1/auth/send-code", json={}, environ_overrides=second_ip)

    assert all(response.status_code == 400 for response in responses)
    assert_rate_limited(blocked)
    assert other_client.status_code == 400


def test_expensive_authenticated_limit_uses_jwt_identity_without_cross_user_contamination(rate_limited_app, rate_limit_db):
    client = rate_limited_app.test_client()
    create_expensive_endpoint_fixture(rate_limited_app)
    endpoint = "/api/v1/plans/100/tasks/generate"

    responses = [
        client.post(endpoint, headers=auth_headers(rate_limited_app, 1))
        for _ in range(configured_limit_count(rate_limited_app, "RATE_LIMIT_GENERATION"))
    ]
    blocked = client.post(endpoint, headers=auth_headers(rate_limited_app, 1))
    other_user = client.post(endpoint, headers=auth_headers(rate_limited_app, 2))

    assert responses[0].status_code == 201
    assert all(response.status_code == 200 for response in responses[1:])
    assert_rate_limited(blocked)
    assert other_user.status_code == 404
    assert other_user.get_json()["error"]["code"] == "PLAN_NOT_FOUND"
