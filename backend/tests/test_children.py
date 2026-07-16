import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Child, User


@pytest.fixture()
def children_db(app):
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def auth_headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def create_user(user_id, phone):
    user = User(id=user_id, phone=phone, nickname="童旅用户")
    db.session.add(user)
    db.session.commit()
    return user


def test_get_children_requires_token(client):
    response = client.get("/api/v1/children")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_get_children_empty_response(client, app, children_db):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.get("/api/v1/children", headers=auth_headers(app, 1))

    assert response.status_code == 200
    assert response.get_json()["data"] == {"children": [], "currentChild": None}


def test_post_child_requires_name(client, app, children_db):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post("/api/v1/children", json={"age": 7}, headers=auth_headers(app, 1))

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_child_rejects_blank_name(client, app, children_db):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post(
        "/api/v1/children",
        json={"name": "   ", "age": 7},
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("age", [2, 13, True])
def test_post_child_rejects_invalid_age(client, app, children_db, age):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post(
        "/api/v1/children",
        json={"name": "小小探索家", "age": age},
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_child_rejects_inconsistent_age_group(client, app, children_db):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post(
        "/api/v1/children",
        json={"name": "小小探索家", "age": 7, "ageGroup": "3-6"},
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_child_rejects_non_array_interests(client, app, children_db):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post(
        "/api/v1/children",
        json={"name": "小小探索家", "age": 7, "interests": "历史"},
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_child_deduplicates_interests(client, app, children_db, monkeypatch):
    with app.app_context():
        create_user(1, "13800138000")

    def fake_create_child(user, payload):
        assert payload["interests"] == ["古建筑", " 古建筑 ", "历史故事"]
        return {
            "id": 10,
            "name": "小小探索家",
            "age": 7,
            "city": None,
            "ageGroup": "7-12",
            "interests": ["古建筑", "历史故事"],
            "isDefault": True,
        }

    monkeypatch.setattr("app.api.v1.children.create_child", fake_create_child)

    response = client.post(
        "/api/v1/children",
        json={
            "name": "小小探索家",
            "age": 7,
            "interests": ["古建筑", " 古建筑 ", "历史故事"],
        },
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 201
    child = response.get_json()["data"]["child"]
    assert child["interests"] == ["古建筑", "历史故事"]
    assert child["ageGroup"] == "7-12"
    assert child["isDefault"] is True


def test_get_child_not_found(client, app, children_db):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.get("/api/v1/children/999", headers=auth_headers(app, 1))

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "CHILD_NOT_FOUND"


def test_patch_rejects_empty_object(client, app, children_db):
    with app.app_context():
        create_user(1, "13800138000")
        child = Child(id=10, user_id=1, name="小小探索家", age=7, age_group="7-12", interests=[], is_default=True)
        db.session.add(child)
        db.session.commit()

    response = client.patch("/api/v1/children/10", json={}, headers=auth_headers(app, 1))

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_patch_rejects_unknown_field(client, app, children_db):
    with app.app_context():
        create_user(1, "13800138000")
        child = Child(id=10, user_id=1, name="小小探索家", age=7, age_group="7-12", interests=[], is_default=True)
        db.session.add(child)
        db.session.commit()

    response = client.patch(
        "/api/v1/children/10",
        json={"nickname": "错误字段"},
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_patch_age_updates_age_group(client, app, children_db):
    with app.app_context():
        create_user(1, "13800138000")
        child = Child(id=10, user_id=1, name="小小探索家", age=6, age_group="3-6", interests=[], is_default=True)
        db.session.add(child)
        db.session.commit()

    response = client.patch("/api/v1/children/10", json={"age": 7}, headers=auth_headers(app, 1))

    assert response.status_code == 200
    child = response.get_json()["data"]["child"]
    assert child["age"] == 7
    assert child["ageGroup"] == "7-12"


def test_patch_rejects_inconsistent_age_group(client, app, children_db):
    with app.app_context():
        create_user(1, "13800138000")
        child = Child(id=10, user_id=1, name="小小探索家", age=7, age_group="7-12", interests=[], is_default=True)
        db.session.add(child)
        db.session.commit()

    response = client.patch(
        "/api/v1/children/10",
        json={"ageGroup": "3-6"},
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_patch_current_default_to_false_is_rejected(client, app, children_db):
    with app.app_context():
        create_user(1, "13800138000")
        child = Child(id=10, user_id=1, name="小小探索家", age=7, age_group="7-12", interests=[], is_default=True)
        db.session.add(child)
        db.session.commit()

    response = client.patch(
        "/api/v1/children/10",
        json={"isDefault": False},
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "DEFAULT_CHILD_REQUIRED"
