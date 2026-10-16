from datetime import datetime
from pathlib import Path

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import event

from app.constants import CHILD_AVATAR_PRESETS, CHILD_PRIVACY_CONSENT_VERSION
from app.extensions import db
from app.models import (
    Attraction,
    Child,
    ExplorationPlan,
    GuideAudioJob,
    GuideCard,
    JourneyRecord,
    Route,
    RouteDay,
    RouteStop,
    Task,
    TaskSubmission,
    User,
)
from app.services.children import delete_child


@pytest.fixture()
def privacy_db(app):
    def enable_foreign_keys(dbapi_connection, _connection_record):
        if dbapi_connection.__class__.__module__.startswith("sqlite3"):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

    with app.app_context():
        event.listen(db.engine, "connect", enable_foreign_keys)
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()
        event.remove(db.engine, "connect", enable_foreign_keys)


def auth_headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def create_user(user_id, phone):
    user = User(id=user_id, phone=phone, nickname=f"监护人{user_id}")
    db.session.add(user)
    db.session.commit()
    return user


def create_payload(**overrides):
    payload = {
        "name": " 小童 ",
        "age": 7,
        "city": " 佛山 ",
        "avatarPreset": "avatar_01",
        "interests": ["历史故事", " 动物 ", "历史故事"],
        "guardianConsent": True,
    }
    payload.update(overrides)
    return payload


def make_child(child_id, user_id, *, name=None, is_default=False, created_at=None, consent_at=None):
    return Child(
        id=child_id,
        user_id=user_id,
        name=name or f"孩子{child_id}",
        age=7,
        age_group="7-12",
        interests=[],
        is_default=is_default,
        created_at=created_at or datetime(2026, 1, 1, 0, 0, child_id % 60),
        guardian_consent_at=consent_at,
        guardian_consent_version=CHILD_PRIVACY_CONSENT_VERSION if consent_at else None,
        guardian_consent_source="child_create" if consent_at else None,
    )


def make_plan(plan_id, user_id, child_id, route_stop_id):
    return ExplorationPlan(
        id=plan_id,
        user_id=user_id,
        child_id=child_id,
        route_stop_id=route_stop_id,
        title=f"探索计划{plan_id}",
        destination="佛山祖庙",
        age_group="7-12",
        duration="2小时",
        interests=["历史故事"],
        status="ready",
    )


def make_task(task_id, plan_id):
    return Task(
        id=task_id,
        plan_id=plan_id,
        sort_order=1,
        title=f"任务{task_id}",
        age_group="7-12",
        duration="10分钟",
        task_type="observe",
        objective="观察一处文化细节",
        steps=[],
        questions=[],
        record_mode="photo",
    )


def test_post_requires_explicit_guardian_consent_and_persists_audit(client, app, privacy_db):
    with app.app_context():
        create_user(1, "13800138000")

    for value in (None, False):
        payload = create_payload()
        if value is None:
            payload.pop("guardianConsent")
        else:
            payload["guardianConsent"] = value
        response = client.post("/api/v1/children", json=payload, headers=auth_headers(app, 1))
        assert response.status_code == 400
        assert response.get_json()["error"]["code"] == "GUARDIAN_CONSENT_REQUIRED"

    response = client.post("/api/v1/children", json=create_payload(), headers=auth_headers(app, 1))

    assert response.status_code == 201
    child_data = response.get_json()["data"]["child"]
    assert child_data == {
        "id": child_data["id"],
        "name": "小童",
        "age": 7,
        "city": "佛山",
        "avatarPreset": "avatar_01",
        "ageGroup": "7-12",
        "interests": ["历史故事", "动物"],
        "isDefault": True,
        "guardianConsentGranted": True,
    }
    assert "guardianConsentAt" not in child_data
    assert "guardianConsentVersion" not in child_data
    assert "guardianConsentSource" not in child_data

    with app.app_context():
        child = db.session.get(Child, child_data["id"])
        assert child.guardian_consent_at is not None
        assert child.guardian_consent_version == CHILD_PRIVACY_CONSENT_VERSION
        assert child.guardian_consent_source == "child_create"


@pytest.mark.parametrize("age", [3, 12])
def test_post_accepts_age_boundaries(client, app, privacy_db, age):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post("/api/v1/children", json=create_payload(age=age), headers=auth_headers(app, 1))

    assert response.status_code == 201
    assert response.get_json()["data"]["child"]["age"] == age


@pytest.mark.parametrize("age", [2, 13, 0, -1, True, False, 7.0, "7"])
def test_post_rejects_non_contract_ages(client, app, privacy_db, age):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post("/api/v1/children", json=create_payload(age=age), headers=auth_headers(app, 1))

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_CHILD_AGE"


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (create_payload(name=" "), "INVALID_CHILD_NAME"),
        (create_payload(name="x" * 51), "INVALID_CHILD_NAME"),
        (create_payload(city="x" * 51), "INVALID_CHILD_CITY"),
        (create_payload(interests="历史故事"), "INVALID_CHILD_INTERESTS"),
        (create_payload(interests=["历史故事", 1]), "INVALID_CHILD_INTERESTS"),
        (create_payload(interests=[" "]), "INVALID_CHILD_INTERESTS"),
        (create_payload(interests=["x" * 31]), "INVALID_CHILD_INTERESTS"),
        (create_payload(interests=[str(index) for index in range(11)]), "INVALID_CHILD_INTERESTS"),
    ],
)
def test_post_validates_private_profile_text_fields(client, app, privacy_db, payload, code):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post("/api/v1/children", json=payload, headers=auth_headers(app, 1))

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == code


@pytest.mark.parametrize("city", [None, ""])
def test_post_city_is_optional_and_normalizes_to_null(client, app, privacy_db, city):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post("/api/v1/children", json=create_payload(city=city), headers=auth_headers(app, 1))

    assert response.status_code == 201
    assert response.get_json()["data"]["child"]["city"] is None


def test_post_allows_an_empty_interest_list(client, app, privacy_db):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post("/api/v1/children", json=create_payload(interests=[]), headers=auth_headers(app, 1))

    assert response.status_code == 201
    assert response.get_json()["data"]["child"]["interests"] == []


def test_post_requires_one_shipped_avatar_preset(client, app, privacy_db):
    with app.app_context():
        create_user(1, "13800138000")

    for index, avatar_preset in enumerate(CHILD_AVATAR_PRESETS, start=1):
        response = client.post(
            "/api/v1/children",
            json=create_payload(name=f"孩子{index}", avatarPreset=avatar_preset),
            headers=auth_headers(app, 1),
        )
        assert response.status_code == 201
        assert response.get_json()["data"]["child"]["avatarPreset"] == avatar_preset


@pytest.mark.parametrize("avatar_preset", [None, "", "avatar_07", "https://example.test/avatar.png", "../avatar_01"])
def test_post_rejects_missing_or_invalid_avatar_preset(client, app, privacy_db, avatar_preset):
    with app.app_context():
        create_user(1, "13800138000")

    payload = create_payload()
    if avatar_preset is None:
        payload.pop("avatarPreset")
    else:
        payload["avatarPreset"] = avatar_preset

    response = client.post("/api/v1/children", json=payload, headers=auth_headers(app, 1))

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_CHILD_AVATAR"


def test_shipped_child_avatar_assets_are_exact_valid_png_files():
    avatar_directory = Path(__file__).resolve().parents[2] / "frontend" / "src" / "static" / "avatars" / "children"
    expected_filenames = {f"{avatar_preset}.png" for avatar_preset in CHILD_AVATAR_PRESETS}

    assert len(CHILD_AVATAR_PRESETS) == 6
    assert {path.name for path in avatar_directory.glob("*.png")} == expected_filenames

    from PIL import Image

    for filename in expected_filenames:
        with Image.open(avatar_directory / filename) as image:
            assert image.format == "PNG"
            assert image.size == (256, 256)
            assert image.getbbox() is not None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ageGroup", "7-12"),
        ("isDefault", True),
        ("guardianConsentGranted", True),
        ("guardianConsentAt", "2026-01-01"),
        ("guardianConsentVersion", "1.0"),
        ("guardianConsentSource", "client"),
    ],
)
def test_post_rejects_read_only_fields(client, app, privacy_db, field, value):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post(
        "/api/v1/children", json=create_payload(**{field: value}), headers=auth_headers(app, 1)
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_patch_updates_profile_without_refreshing_existing_consent(client, app, privacy_db):
    prior_consent = datetime(2026, 2, 3, 4, 5, 6)
    with app.app_context():
        create_user(1, "13800138000")
        child = make_child(10, 1, is_default=True, consent_at=prior_consent)
        db.session.add(child)
        db.session.commit()

    response = client.patch(
        "/api/v1/children/10",
        json={"name": "新名字", "age": 8, "city": "", "interests": ["动物", " 动物 ", "手工"]},
        headers=auth_headers(app, 1),
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["child"]["city"] is None
    assert response.get_json()["data"]["child"]["ageGroup"] == "7-12"
    assert response.get_json()["data"]["child"]["interests"] == ["动物", "手工"]
    with app.app_context():
        child = db.session.get(Child, 10)
        assert child.guardian_consent_at == prior_consent
        assert child.guardian_consent_version == CHILD_PRIVACY_CONSENT_VERSION
        assert child.guardian_consent_source == "child_create"


def test_patch_allows_one_legacy_consent_backfill_without_future_refresh(client, app, privacy_db):
    with app.app_context():
        create_user(1, "13800138000")
        db.session.add(make_child(10, 1, is_default=True))
        db.session.commit()

    backfill = client.patch(
        "/api/v1/children/10", json={"guardianConsent": True}, headers=auth_headers(app, 1)
    )
    with app.app_context():
        child = db.session.get(Child, 10)
        consent_at = child.guardian_consent_at
        assert consent_at is not None
        assert child.guardian_consent_version == CHILD_PRIVACY_CONSENT_VERSION
        assert child.guardian_consent_source == "child_edit"

    ordinary_edit = client.patch(
        "/api/v1/children/10", json={"city": "佛山"}, headers=auth_headers(app, 1)
    )
    revoke = client.patch(
        "/api/v1/children/10", json={"guardianConsent": False}, headers=auth_headers(app, 1)
    )

    assert backfill.status_code == 200
    assert ordinary_edit.status_code == 200
    assert revoke.status_code == 400
    assert revoke.get_json()["error"]["code"] == "GUARDIAN_CONSENT_CANNOT_BE_REVOKED"
    with app.app_context():
        child = db.session.get(Child, 10)
        assert child.guardian_consent_at == consent_at
        assert child.guardian_consent_version == CHILD_PRIVACY_CONSENT_VERSION
        assert child.guardian_consent_source == "child_edit"


def test_patch_accepts_shipped_avatar_presets_and_rejects_invalid_values(client, app, privacy_db):
    with app.app_context():
        create_user(1, "13800138000")
        db.session.add(make_child(10, 1, is_default=True))
        db.session.commit()

    selected = client.patch(
        "/api/v1/children/10", json={"avatarPreset": "avatar_06"}, headers=auth_headers(app, 1)
    )
    retained = client.patch(
        "/api/v1/children/10", json={"city": "佛山"}, headers=auth_headers(app, 1)
    )
    invalid = client.patch(
        "/api/v1/children/10", json={"avatarPreset": "forest-fox"}, headers=auth_headers(app, 1)
    )
    null_value = client.patch(
        "/api/v1/children/10", json={"avatarPreset": None}, headers=auth_headers(app, 1)
    )
    read_only = client.patch(
        "/api/v1/children/10", json={"guardianConsentGranted": True}, headers=auth_headers(app, 1)
    )

    assert selected.status_code == 200
    assert selected.get_json()["data"]["child"]["avatarPreset"] == "avatar_06"
    assert retained.status_code == 200
    assert retained.get_json()["data"]["child"]["avatarPreset"] == "avatar_06"
    assert invalid.status_code == 400
    assert invalid.get_json()["error"]["code"] == "INVALID_CHILD_AVATAR"
    assert null_value.status_code == 400
    assert null_value.get_json()["error"]["code"] == "INVALID_CHILD_AVATAR"
    assert read_only.status_code == 400
    assert read_only.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_detail_and_patch_are_owner_scoped_and_hide_audit_fields(client, app, privacy_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_user(2, "13900139000")
        db.session.add(make_child(10, 2, is_default=True, consent_at=datetime(2026, 1, 1)))
        db.session.commit()

    detail = client.get("/api/v1/children/10", headers=auth_headers(app, 2))
    other_detail = client.get("/api/v1/children/10", headers=auth_headers(app, 1))
    other_patch = client.patch("/api/v1/children/10", json={"name": "越权"}, headers=auth_headers(app, 1))

    assert detail.status_code == 200
    payload = detail.get_json()["data"]["child"]
    assert payload["guardianConsentGranted"] is True
    assert not {"guardianConsentAt", "guardianConsentVersion", "guardianConsentSource"} & set(payload)
    assert other_detail.status_code == 404
    assert other_detail.get_json()["error"]["code"] == "CHILD_NOT_FOUND"
    assert other_patch.status_code == 404
    assert other_patch.get_json()["error"]["code"] == "CHILD_NOT_FOUND"


class FakeAudioStorage:
    def __init__(self, *, failure=None):
        self.deleted_keys = []
        self.failure = failure

    def delete(self, *, object_key):
        self.deleted_keys.append(object_key)
        if self.failure is not None:
            raise self.failure


def test_delete_child_removes_only_its_closure_and_preserves_shared_route_and_assets(app, privacy_db, tmp_path):
    task_root = tmp_path / "task-images"
    record_root = tmp_path / "record-images"
    app.config["TASK_IMAGE_UPLOAD_DIR"] = str(task_root)
    app.config["RECORD_IMAGE_UPLOAD_DIR"] = str(record_root)
    a_key = "task-images/child-a.png"
    b_key = "task-images/child-b.png"
    audio_key = f"guide-audio/700/{'a' * 64}/{'b' * 32}.mp3"
    storage = FakeAudioStorage()

    with app.app_context():
        owner = create_user(1, "13800138000")
        create_user(2, "13900139000")
        db.session.add_all([
            make_child(10, 1, name="孩子甲", is_default=True),
            make_child(11, 1, name="孩子乙"),
            make_child(20, 2, name="其他用户", is_default=True),
            Attraction(id=1, name="佛山祖庙", city="佛山", summary="文化地标", tags=[]),
            Route(id=1, user_id=1, title="家庭行程", city="佛山"),
            RouteDay(id=10, route_id=1, day_number=1),
            RouteStop(id=100, route_day_id=10, attraction_id=1, sort_order=1),
        ])
        db.session.commit()
        db.session.add_all([
            make_plan(1000, 1, 10, 100),
            make_plan(1001, 1, 11, 100),
            make_plan(1002, 2, 20, None),
            make_task(2000, 1000),
            make_task(2001, 1001),
            make_task(2002, 1002),
            TaskSubmission(id=3000, task_id=2000, status="completed", image_url=a_key, note="甲的发现"),
            TaskSubmission(id=3001, task_id=2001, status="completed", image_url=b_key, note="乙的发现"),
            TaskSubmission(id=3002, task_id=2002, status="completed", image_url="task-images/other-user.png", note="其他用户的发现"),
            GuideCard(
                id=700,
                plan_id=1000,
                child_intro=[],
                questions=[],
                focus_items=[],
                audio_status="ready",
                audio_object_key=audio_key,
                audio_source_hash="a" * 64,
                audio_generation_token="b" * 32,
            ),
            JourneyRecord(id=800, plan_id=1000, cover_submission_id=3000, status="finalized", snapshot={}),
        ])
        db.session.commit()
        db.session.add(
            GuideAudioJob(
                id=900,
                guide_id=700,
                guide_version=1,
                source_hash="a" * 64,
                generation_token="b" * 32,
                status="completed",
                attempt_count=1,
            )
        )
        db.session.commit()
        (task_root / "child-a.png").parent.mkdir(parents=True)
        (task_root / "child-a.png").write_bytes(b"child-a")
        (task_root / "child-b.png").write_bytes(b"child-b")
        (task_root / "other-user.png").write_bytes(b"other-user")
        (record_root / "800").mkdir(parents=True)
        (record_root / "800" / "snapshot.png").write_bytes(b"record")

        result = delete_child(owner, 10, audio_storage=storage)

        assert result["deletedChildId"] == 10
        assert [item["id"] for item in result["children"]] == [11]
        assert result["currentChild"]["id"] == 11
        assert db.session.get(Child, 10) is None
        assert db.session.get(ExplorationPlan, 1000) is None
        assert db.session.get(Task, 2000) is None
        assert db.session.get(TaskSubmission, 3000) is None
        assert db.session.get(GuideCard, 700) is None
        assert db.session.get(GuideAudioJob, 900) is None
        assert db.session.get(JourneyRecord, 800) is None
        assert db.session.get(Child, 11) is not None
        assert db.session.get(ExplorationPlan, 1001) is not None
        assert db.session.get(Task, 2001) is not None
        assert db.session.get(TaskSubmission, 3001) is not None
        assert db.session.get(Child, 20) is not None
        assert db.session.get(ExplorationPlan, 1002) is not None
        assert db.session.get(Task, 2002) is not None
        assert db.session.get(TaskSubmission, 3002) is not None
        assert db.session.get(Route, 1) is not None
        assert db.session.get(RouteDay, 10) is not None
        assert db.session.get(RouteStop, 100) is not None
        assert not (task_root / "child-a.png").exists()
        assert (task_root / "child-b.png").exists()
        assert (task_root / "other-user.png").exists()
        assert not (record_root / "800").exists()
        assert storage.deleted_keys == [audio_key]


def test_asset_cleanup_failure_never_rolls_back_committed_child_deletion(app, privacy_db):
    audio_key = f"guide-audio/700/{'a' * 64}/{'b' * 32}.mp3"
    with app.app_context():
        owner = create_user(1, "13800138000")
        db.session.add_all([
            make_child(10, 1, is_default=True),
            make_plan(1000, 1, 10, None),
            GuideCard(
                id=700,
                plan_id=1000,
                child_intro=[],
                questions=[],
                focus_items=[],
                audio_status="ready",
                audio_object_key=audio_key,
                audio_source_hash="a" * 64,
                audio_generation_token="b" * 32,
            ),
        ])
        db.session.commit()

        storage = FakeAudioStorage(failure=OSError("storage unavailable"))
        result = delete_child(owner, 10, audio_storage=storage)

        assert result == {"deletedChildId": 10, "children": [], "currentChild": None}
        assert db.session.get(Child, 10) is None
        assert db.session.get(ExplorationPlan, 1000) is None
        assert db.session.get(GuideCard, 700) is None
        assert storage.deleted_keys == [audio_key]


def test_delete_endpoint_hides_other_users_and_repairs_default_deterministically(client, app, privacy_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_user(2, "13900139000")
        db.session.add_all([
            make_child(10, 1, is_default=True, created_at=datetime(2026, 1, 1)),
            make_child(11, 1, created_at=datetime(2026, 1, 2)),
            make_child(12, 1, created_at=datetime(2026, 1, 3)),
            make_child(20, 2, is_default=True),
        ])
        db.session.commit()

    no_token = client.delete("/api/v1/children/10")
    other_user = client.delete("/api/v1/children/20", headers=auth_headers(app, 1))
    missing = client.delete("/api/v1/children/999", headers=auth_headers(app, 1))
    first = client.delete("/api/v1/children/10", headers=auth_headers(app, 1))
    with app.app_context():
        assert [child.id for child in Child.query.filter_by(user_id=1, is_default=True).all()] == [11]
    second = client.delete("/api/v1/children/12", headers=auth_headers(app, 1))
    with app.app_context():
        assert [child.id for child in Child.query.filter_by(user_id=1, is_default=True).all()] == [11]
    last = client.delete("/api/v1/children/11", headers=auth_headers(app, 1))

    assert no_token.status_code == 401
    assert other_user.status_code == 404
    assert other_user.get_json()["error"]["code"] == "CHILD_NOT_FOUND"
    assert missing.status_code == 404
    assert first.status_code == 200
    assert first.get_json()["data"]["currentChild"]["id"] == 11
    assert second.status_code == 200
    assert second.get_json()["data"]["currentChild"]["id"] == 11
    assert last.status_code == 200
    assert last.get_json()["data"] == {"deletedChildId": 11, "children": [], "currentChild": None}
    with app.app_context():
        assert Child.query.filter_by(user_id=1).count() == 0
        assert Child.query.filter_by(user_id=2).count() == 1
