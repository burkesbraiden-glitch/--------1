import json
from datetime import datetime

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import event

from app.extensions import db
from app.models import (
    Attraction,
    Child,
    ExplorationPlan,
    GuideAudioJob,
    GuideCard,
    JourneyRecord,
    PhoneVerificationCode,
    Route,
    RouteDay,
    RouteStop,
    Task,
    TaskSubmission,
    User,
)
from app.services.account import delete_account


@pytest.fixture()
def account_db(app):
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


class FakeAudioStorage:
    def __init__(self):
        self.deleted_keys = []

    def delete(self, *, object_key):
        self.deleted_keys.append(object_key)


def seed_account_graph():
    audio_key = f"guide-audio/401/{'a' * 64}/{'b' * 32}.mp3"
    image_key = "task-images/account-owner.png"
    other_image_key = "task-images/other-account.png"
    owner = User(
        id=1,
        phone="13800138000",
        nickname="监护人甲",
        city="佛山",
        created_at=datetime(2026, 1, 2, 3, 4, 5),
    )
    other_user = User(id=2, phone="13900139000", nickname="监护人乙")
    owner_child = Child(
        id=10,
        user_id=1,
        name="小童",
        age=7,
        city="佛山",
        avatar_preset="avatar_01",
        age_group="7-12",
        interests=["历史故事"],
        is_default=True,
        guardian_consent_at=datetime(2026, 1, 2, 3, 4, 5),
    )
    other_child = Child(
        id=20,
        user_id=2,
        name="其他孩子",
        age=8,
        avatar_preset="avatar_02",
        age_group="7-12",
        interests=["动物"],
        is_default=True,
        guardian_consent_at=datetime(2026, 1, 2, 3, 4, 5),
    )
    attraction = Attraction(id=1, name="佛山祖庙", city="佛山", summary="文化地标", tags=[])
    route = Route(id=30, user_id=1, title="家庭佛山行", city="佛山", status="ready")
    other_route = Route(id=40, user_id=2, title="其他家庭行", city="广州", status="draft")
    day = RouteDay(id=31, route_id=30, day_number=1, title="第一天")
    stop = RouteStop(id=32, route_day_id=31, attraction_id=1, sort_order=1, note="慢慢观察")
    plan = ExplorationPlan(
        id=100,
        user_id=1,
        child_id=10,
        route_stop_id=32,
        title="祖庙探索",
        destination="佛山祖庙",
        age_group="7-12",
        duration="2小时",
        interests=["历史故事"],
        source_snapshot={"internalOnly": "do not export"},
        status="completed",
        completed_at=datetime(2026, 1, 3, 4, 5, 6),
    )
    other_plan = ExplorationPlan(
        id=200,
        user_id=2,
        child_id=20,
        route_stop_id=None,
        title="其他探索",
        destination="其他地点",
        age_group="7-12",
        duration="1小时",
        interests=["动物"],
        status="ready",
    )
    task = Task(
        id=300,
        plan_id=100,
        sort_order=1,
        title="观察屋顶",
        subtitle="找一找颜色",
        age_group="7-12",
        duration="10分钟",
        task_type="observe",
        summary="看见细节",
        objective="观察一处文化细节",
        steps=["抬头看"],
        questions=["看到了什么？"],
        record_mode="photo",
        theme="history",
    )
    other_task = Task(
        id=301,
        plan_id=200,
        sort_order=1,
        title="其他任务",
        age_group="7-12",
        duration="10分钟",
        task_type="observe",
        objective="观察",
        steps=[],
        questions=[],
        record_mode="photo",
    )
    submission = TaskSubmission(
        id=350,
        task_id=300,
        status="completed",
        image_url=image_key,
        note="屋顶很漂亮",
        completed_at=datetime(2026, 1, 3, 4, 5, 6),
    )
    other_submission = TaskSubmission(
        id=351,
        task_id=301,
        status="completed",
        image_url=other_image_key,
        note="其他用户的记录",
    )
    guide = GuideCard(
        id=401,
        plan_id=100,
        child_intro=["一起观察"],
        questions=["你发现了什么？"],
        focus_items=["屋顶"],
        narration_text="这是讲解内容",
        guide_version=2,
        audio_status="ready",
        audio_url="https://must-not-export.example/audio.mp3",
        audio_object_key=audio_key,
        audio_source_hash="a" * 64,
        audio_generation_token="b" * 32,
        audio_duration_sec=36,
        audio_generated_at=datetime(2026, 1, 3, 4, 5, 6),
    )
    job = GuideAudioJob(
        id=450,
        guide_id=401,
        guide_version=2,
        source_hash="a" * 64,
        generation_token="b" * 32,
        status="completed",
        attempt_count=1,
    )
    record = JourneyRecord(
        id=500,
        plan_id=100,
        custom_title="祖庙发现",
        summary="一次探索",
        cover_submission_id=350,
        status="finalized",
        finalized_at=datetime(2026, 1, 3, 4, 5, 6),
        snapshot={"imageAssets": [{"storageKey": "record-images/500/secret.png"}]},
    )
    verification_code = PhoneVerificationCode(
        phone="13800138000",
        code_hash="secret-code-hash",
        sent_at=datetime(2026, 1, 3, 4, 5, 6),
        expires_at=datetime(2026, 1, 3, 4, 10, 6),
    )
    db.session.add_all([owner, other_user, owner_child, other_child, attraction, route, other_route, day, stop])
    db.session.commit()
    db.session.add_all([plan, other_plan, task, other_task])
    db.session.commit()
    db.session.add_all([submission, other_submission, guide, job, record, verification_code])
    db.session.commit()
    return {
        "owner": owner,
        "audioKey": audio_key,
        "imageKey": image_key,
        "otherImageKey": other_image_key,
    }


def test_export_requires_current_jwt_and_uses_a_safe_explicit_contract(client, app, account_db):
    with app.app_context():
        seed_account_graph()

    assert client.get("/api/v1/account/export").status_code == 401
    response = client.get("/api/v1/account/export", headers=auth_headers(app, 1))

    assert response.status_code == 200
    exported = response.get_json()["data"]["export"]
    assert set(exported) == {
        "formatVersion", "user", "children", "routes", "routeDays", "routeStops",
        "plans", "tasks", "taskSubmissions", "guideCards", "journeyRecords",
    }
    assert exported["user"] == {
        "id": 1,
        "nickname": "监护人甲",
        "city": "佛山",
        "createdAt": "2026-01-02T03:04:05Z",
        "updatedAt": exported["user"]["updatedAt"],
    }
    assert exported["children"][0]["guardianConsentGranted"] is True
    assert exported["routes"][0]["id"] == 30
    assert exported["routeDays"][0]["routeId"] == 30
    assert exported["routeStops"][0]["routeDayId"] == 31
    assert exported["plans"][0]["routeStopId"] == 32
    assert exported["tasks"][0]["planId"] == 100
    assert exported["taskSubmissions"][0]["hasImage"] is True
    assert exported["guideCards"][0]["hasAudio"] is True
    assert exported["journeyRecords"][0]["hasImages"] is True
    assert exported["plans"][0]["completedAt"].endswith("Z")

    serialized = json.dumps(exported, ensure_ascii=False)
    for sensitive_value in [
        "13800138000", "13900139000", "secret-code-hash", "internalOnly",
        "task-images/", "record-images/", "audio_object_key", "https://must-not-export.example",
        "guide-audio/", "audio_source_hash", "audio_generation_token",
    ]:
        assert sensitive_value not in serialized
    assert "phone" not in exported["user"]
    assert "sourceSnapshot" not in exported["plans"][0]


def test_export_isolated_to_the_authenticated_account(client, app, account_db):
    with app.app_context():
        seed_account_graph()

    response = client.get("/api/v1/account/export", headers=auth_headers(app, 2))

    assert response.status_code == 200
    exported = response.get_json()["data"]["export"]
    assert [child["id"] for child in exported["children"]] == [20]
    assert [route["id"] for route in exported["routes"]] == [40]
    assert [plan["id"] for plan in exported["plans"]] == [200]
    assert [task["id"] for task in exported["tasks"]] == [301]
    assert [submission["id"] for submission in exported["taskSubmissions"]] == [351]
    assert exported["guideCards"] == []
    assert exported["journeyRecords"] == []


def test_delete_account_removes_its_complete_closure_and_only_its_assets(app, account_db, tmp_path):
    task_root = tmp_path / "task-images"
    record_root = tmp_path / "record-images"
    app.config["TASK_IMAGE_UPLOAD_DIR"] = str(task_root)
    app.config["RECORD_IMAGE_UPLOAD_DIR"] = str(record_root)
    storage = FakeAudioStorage()

    with app.app_context():
        seeded = seed_account_graph()
        (task_root / "account-owner.png").parent.mkdir(parents=True)
        (task_root / "account-owner.png").write_bytes(b"owner")
        (task_root / "other-account.png").write_bytes(b"other")
        (record_root / "500").mkdir(parents=True)
        (record_root / "500" / "snapshot.png").write_bytes(b"record")

        assert delete_account(seeded["owner"], audio_storage=storage) == {"deleted": True}

        for model, model_id in [
            (User, 1), (Child, 10), (ExplorationPlan, 100), (Task, 300),
            (TaskSubmission, 350), (GuideCard, 401), (GuideAudioJob, 450),
            (JourneyRecord, 500), (Route, 30), (RouteDay, 31), (RouteStop, 32),
        ]:
            assert db.session.get(model, model_id) is None
        assert db.session.get(PhoneVerificationCode, "13800138000") is None
        for model, model_id in [(User, 2), (Child, 20), (ExplorationPlan, 200), (Task, 301), (TaskSubmission, 351)]:
            assert db.session.get(model, model_id) is not None
        assert db.session.get(Route, 40) is not None
        assert not (task_root / "account-owner.png").exists()
        assert (task_root / "other-account.png").exists()
        assert not (record_root / "500").exists()
        assert storage.deleted_keys == [seeded["audioKey"]]


def test_delete_endpoint_uses_the_current_account_only(client, app, account_db):
    with app.app_context():
        seed_account_graph()

    assert client.delete("/api/v1/account").status_code == 401
    response = client.delete("/api/v1/account", json={"userId": 2}, headers=auth_headers(app, 1))

    assert response.status_code == 200
    assert response.get_json()["data"] == {"deleted": True}
    with app.app_context():
        assert db.session.get(User, 1) is None
        assert db.session.get(User, 2) is not None
        assert db.session.get(ExplorationPlan, 200) is not None
        assert db.session.get(Route, 40) is not None
