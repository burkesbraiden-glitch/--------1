import importlib

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import text

from app.extensions import db
from app.models import Child, ExplorationPlan, GuideCard, User
from app.services.audio_storage import AudioStorageError


class FakeTTSProvider:
    def __init__(self, *, failure=None, duration_sec=97):
        self.failure = failure
        self.duration_sec = duration_sec
        self.calls = []

    def synthesize(self, *, text, language, voice, format):
        self.calls.append(
            {
                "text": text,
                "language": language,
                "voice": voice,
                "format": format,
            }
        )
        if self.failure is not None:
            raise self.failure
        return {
            "audio_bytes": b"fake-mp3-bytes",
            "content_type": "audio/mpeg",
            "duration_sec": self.duration_sec,
        }


class FakeAudioStorage:
    def __init__(self, *, failure=None):
        self.failure = failure
        self.objects = {}
        self.deleted_keys = []
        self.signed_url_calls = []

    def put(self, *, object_key, audio_bytes, content_type):
        if self.failure is not None:
            raise self.failure
        self.objects[object_key] = {
            "audio_bytes": audio_bytes,
            "content_type": content_type,
        }
        return object_key

    def delete(self, *, object_key):
        self.deleted_keys.append(object_key)
        self.objects.pop(object_key, None)

    def create_signed_url(self, *, object_key, expires_in_seconds):
        self.signed_url_calls.append((object_key, expires_in_seconds))
        return f"https://signed.example.test/{object_key}?expires={expires_in_seconds}"


class InterruptingAudioStorage(FakeAudioStorage):
    def __init__(self, *, on_first_put):
        super().__init__()
        self.on_first_put = on_first_put
        self.put_count = 0

    def put(self, *, object_key, audio_bytes, content_type):
        persisted_key = super().put(
            object_key=object_key,
            audio_bytes=audio_bytes,
            content_type=content_type,
        )
        self.put_count += 1
        if self.put_count == 1:
            self.on_first_put()
        return persisted_key


class RecoveringSigningAudioStorage(FakeAudioStorage):
    def __init__(self, *, signing_error=None):
        super().__init__()
        self.signing_error = signing_error

    def create_signed_url(self, *, object_key, expires_in_seconds):
        self.signed_url_calls.append((object_key, expires_in_seconds))
        if self.signing_error is not None:
            raise self.signing_error
        return f"https://signed.example.test/{object_key}?expires={expires_in_seconds}"


@pytest.fixture()
def audio_db(app):
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def auth_headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def create_audio_fixture(*, user_id=1, plan_id=100, guide_id=500):
    user = User(id=user_id, phone=f"138{user_id:08d}", nickname="童旅用户")
    child = Child(
        id=user_id * 10,
        user_id=user.id,
        name="小小探索家",
        age=7,
        age_group="7-12",
        interests=["历史故事"],
        is_default=True,
    )
    plan = ExplorationPlan(
        id=plan_id,
        user_id=user.id,
        child_id=child.id,
        title="故宫亲子探索",
        destination="故宫博物院",
        age_group="7-12",
        duration="3小时",
        interests=["历史故事", "建筑礼仪"],
        status="ready",
    )
    guide = GuideCard(
        id=guide_id,
        plan_id=plan.id,
        child_intro=[
            "故宫以前是皇帝和家人生活、工作的地方。",
            "屋顶、宫门和台阶里藏着很多古代礼仪。",
            "今天不用记很多名字，认真观察就很好。",
        ],
        questions=["你发现屋顶上有什么特别的东西？"],
        focus_items=["屋顶", "宫门", "颜色"],
        audio_url=None,
    )
    db.session.add_all([user, child, plan, guide])
    db.session.commit()
    return user, plan, guide


def guide_audio_service(*, tts_provider=None, storage=None):
    module = importlib.import_module("app.services.guide_audio")
    return module.GuideAudioService(
        tts_provider=tts_provider or FakeTTSProvider(),
        storage=storage or FakeAudioStorage(),
    )


def narration_builder():
    module = importlib.import_module("app.services.guide_narration")
    return module.build_narration_text


def source_hash(**kwargs):
    module = importlib.import_module("app.services.guide_narration")
    return module.build_audio_source_hash(**kwargs)


def job_field(job, name):
    if isinstance(job, dict):
        return job[name]
    return getattr(job, name)


def require_audio_job_model():
    try:
        return importlib.import_module("app.models.guide_audio_job").GuideAudioJob
    except ModuleNotFoundError as error:
        pytest.fail(f"P8.2B2 AudioJob contract is missing: {error}")


def ensure_audio_job_table():
    model = require_audio_job_model()
    model.__table__.create(bind=db.engine, checkfirst=True)
    return model


def test_new_guide_card_has_versioned_audio_domain_fields():
    table = GuideCard.__table__

    for field in (
        "narration_text",
        "guide_version",
        "audio_status",
        "audio_object_key",
        "audio_source_hash",
        "audio_generation_token",
        "audio_duration_sec",
        "audio_generated_at",
        "audio_error_code",
    ):
        assert field in table.c

    assert table.c.guide_version.default.arg == 1
    assert table.c.audio_status.default.arg == "none"


def test_narration_builder_creates_child_friendly_script_without_field_names(audio_db):
    _user, plan, guide = create_audio_fixture()

    text = narration_builder()(plan=plan, guide=guide)

    assert "故宫博物院" in text
    assert "屋顶" in text
    assert "你发现屋顶上有什么特别的东西？" in text
    assert "childIntro" not in text
    assert "questions" not in text
    assert "focusItems" not in text


def test_narration_builder_rejects_insufficient_source_content(audio_db):
    _user, plan, guide = create_audio_fixture()
    guide.child_intro = []
    guide.questions = []
    guide.focus_items = []

    with pytest.raises(Exception, match="NARRATION"):
        narration_builder()(plan=plan, guide=guide)


def test_audio_source_hash_is_stable_and_excludes_timestamps():
    payload = {
        "narration_text": "我们现在来到故宫博物院，一起看看屋顶。",
        "language": "zh-CN",
        "voice_profile_id": "warm-guide-v1",
        "tts_config_version": "tts-config-v1",
        "output_format": "mp3",
    }

    first = source_hash(**payload)
    second = source_hash(**payload)

    assert first == second
    assert len(first) == 64


def test_audio_source_hash_changes_with_narration_or_voice_configuration():
    payload = {
        "narration_text": "我们现在来到故宫博物院，一起看看屋顶。",
        "language": "zh-CN",
        "voice_profile_id": "warm-guide-v1",
        "tts_config_version": "tts-config-v1",
        "output_format": "mp3",
    }

    baseline = source_hash(**payload)
    assert source_hash(**{**payload, "narration_text": "我们现在来到故宫博物院，一起看看宫门。"}) != baseline
    assert source_hash(**{**payload, "voice_profile_id": "warm-guide-v2"}) != baseline
    assert source_hash(**{**payload, "tts_config_version": "tts-config-v2"}) != baseline
    assert source_hash(**{**payload, "output_format": "ogg"}) != baseline


def test_enqueue_transitions_none_to_pending_and_is_idempotent(audio_db):
    user, plan, guide = create_audio_fixture()
    service = guide_audio_service()

    first = service.request_audio_generation(user=user, plan_id=plan.id)
    second = service.request_audio_generation(user=user, plan_id=plan.id)

    db.session.refresh(guide)
    assert guide.audio_status == "pending"
    assert guide.guide_version == 1
    assert job_field(first, "source_hash") == job_field(second, "source_hash")
    assert job_field(first, "generation_token") == job_field(second, "generation_token")
    assert job_field(first, "created") is True
    assert job_field(second, "created") is False


def test_worker_claims_pending_job_then_marks_ready_with_provider_duration(audio_db):
    user, plan, guide = create_audio_fixture()
    tts = FakeTTSProvider(duration_sec=123)
    storage = FakeAudioStorage()
    service = guide_audio_service(tts_provider=tts, storage=storage)
    job = service.request_audio_generation(user=user, plan_id=plan.id)

    service.claim_audio_generation(job)
    db.session.refresh(guide)
    assert guide.audio_status == "generating"

    result = service.process_audio_generation(job)
    db.session.refresh(guide)
    assert result.status == "ready"
    assert guide.audio_status == "ready"
    assert guide.audio_object_key
    assert guide.audio_duration_sec == 123
    assert len(tts.calls) == 1


def test_ready_requires_an_object_key_and_non_ready_cannot_keep_public_url(audio_db):
    _user, _plan, guide = create_audio_fixture()
    service = guide_audio_service()

    guide.audio_status = "ready"
    guide.audio_object_key = None
    with pytest.raises(Exception, match="AUDIO_STATE_INVALID"):
        service.validate_audio_state(guide)

    guide.audio_status = "failed"
    guide.audio_url = "https://must-not-be-public.example.test/old.mp3"
    assert service.validate_audio_state(guide) == "failed"


def test_provider_failure_marks_audio_failed_without_regenerating_guide(audio_db, monkeypatch):
    user, plan, guide = create_audio_fixture()
    tts = FakeTTSProvider(failure=RuntimeError("provider unavailable"))
    service = guide_audio_service(tts_provider=tts)
    job = service.request_audio_generation(user=user, plan_id=plan.id)
    guide_snapshot = (list(guide.child_intro), list(guide.questions), list(guide.focus_items), guide.id)

    guides_module = importlib.import_module("app.services.guides")
    monkeypatch.setattr(guides_module, "generate_guide", lambda *_args, **_kwargs: pytest.fail("audio failure regenerated guide"))

    result = service.process_audio_generation(job)
    db.session.refresh(guide)
    assert result.status == "failed"
    assert guide.audio_status == "failed"
    assert guide_snapshot == (guide.child_intro, guide.questions, guide.focus_items, guide.id)


def test_storage_failure_marks_audio_failed_without_regenerating_guide(audio_db, monkeypatch):
    user, plan, guide = create_audio_fixture()
    storage = FakeAudioStorage(failure=RuntimeError("storage unavailable"))
    service = guide_audio_service(storage=storage)
    job = service.request_audio_generation(user=user, plan_id=plan.id)

    guides_module = importlib.import_module("app.services.guides")
    monkeypatch.setattr(guides_module, "generate_guide", lambda *_args, **_kwargs: pytest.fail("storage failure regenerated guide"))

    result = service.process_audio_generation(job)
    db.session.refresh(guide)
    assert result.status == "failed"
    assert guide.audio_status == "failed"


def test_retry_only_allows_failed_audio_and_never_regenerates_guide(audio_db, monkeypatch):
    user, plan, guide = create_audio_fixture()
    service = guide_audio_service()

    with pytest.raises(Exception, match="AUDIO_RETRY_NOT_ALLOWED"):
        service.request_audio_generation(user=user, plan_id=plan.id, retry=True)

    guide.audio_status = "failed"
    guides_module = importlib.import_module("app.services.guides")
    monkeypatch.setattr(guides_module, "generate_guide", lambda *_args, **_kwargs: pytest.fail("retry regenerated guide"))

    job = service.request_audio_generation(user=user, plan_id=plan.id, retry=True)
    db.session.refresh(guide)
    assert guide.audio_status == "pending"
    assert job_field(job, "created") is True


def test_guide_content_change_invalidates_ready_audio_and_stale_worker_cleans_up(audio_db):
    user, plan, guide = create_audio_fixture()
    service = None

    def switch_to_v2():
        guide.child_intro = ["故宫的屋顶和宫门都值得慢慢观察。"]
        db.session.commit()
        service.request_audio_generation(user=user, plan_id=plan.id)

    storage = InterruptingAudioStorage(on_first_put=switch_to_v2)
    service = guide_audio_service(storage=storage)
    v1_job = service.request_audio_generation(user=user, plan_id=plan.id)

    stale_result = service.process_audio_generation(v1_job)
    db.session.refresh(guide)
    assert stale_result.status == "stale"
    assert guide.audio_status == "pending"
    assert guide.audio_source_hash != job_field(v1_job, "source_hash")
    assert storage.deleted_keys


def test_get_guide_returns_signed_url_only_for_current_ready_audio(audio_db, app, client, monkeypatch):
    _user, plan, guide = create_audio_fixture()
    storage = FakeAudioStorage()
    guide.audio_status = "ready"
    guide.audio_object_key = "guide-audio/500/current.mp3"
    guide.narration_text = narration_builder()(plan=plan, guide=guide)
    guide.audio_source_hash = source_hash(
        narration_text=guide.narration_text,
        language="zh-CN",
        voice_profile_id="warm-guide-v1",
        tts_config_version="p8-2b2-edge-v1",
        output_format="mp3",
    )
    guide.audio_duration_sec = 97
    guide.audio_url = "https://database.example.test/must-not-be-returned.mp3"
    db.session.commit()

    guides_module = importlib.import_module("app.services.guides")
    monkeypatch.setattr(guides_module, "get_audio_storage", lambda: storage, raising=False)

    response = client.get(f"/api/v1/plans/{plan.id}/guide", headers=auth_headers(app, 1))
    guide_payload = response.get_json()["data"]["guide"]
    second_response = client.get(f"/api/v1/plans/{plan.id}/guide", headers=auth_headers(app, 1))
    second_guide_payload = second_response.get_json()["data"]["guide"]

    assert response.status_code == 200
    assert second_response.status_code == 200
    assert guide_payload["audioStatus"] == "ready"
    assert guide_payload["audioDurationSec"] == 97
    assert guide_payload["audioUrl"].startswith("https://signed.example.test/")
    assert second_guide_payload["audioUrl"].startswith("https://signed.example.test/")
    assert len(storage.signed_url_calls) == 2
    assert guide.audio_url == "https://database.example.test/must-not-be-returned.mp3"
    assert "audioObjectKey" not in guide_payload
    assert "audioGenerationToken" not in guide_payload
    assert "database.example.test" not in guide_payload["audioUrl"]


def test_get_guide_degrades_signer_failure_without_mutating_ready_audio(audio_db, app, client, monkeypatch):
    _user, plan, guide = create_audio_fixture()
    storage = RecoveringSigningAudioStorage(
        signing_error=AudioStorageError("AUDIO_STORAGE_SIGNING_FAILED", "Signer unavailable")
    )
    guide.audio_status = "ready"
    guide.audio_object_key = "guide-audio/500/current.mp3"
    guide.narration_text = narration_builder()(plan=plan, guide=guide)
    guide.audio_source_hash = source_hash(
        narration_text=guide.narration_text,
        language="zh-CN",
        voice_profile_id="warm-guide-v1",
        tts_config_version="p8-2b2-edge-v1",
        output_format="mp3",
    )
    guide.audio_duration_sec = 97
    db.session.commit()
    snapshot = (
        guide.audio_status,
        guide.audio_object_key,
        guide.audio_source_hash,
        guide.audio_duration_sec,
    )

    guides_module = importlib.import_module("app.services.guides")
    guide_audio_module = importlib.import_module("app.services.guide_audio")
    monkeypatch.setattr(guides_module, "get_audio_storage", lambda: storage)
    monkeypatch.setattr(guides_module, "generate_guide", lambda *_args, **_kwargs: pytest.fail("GET regenerated guide"))
    monkeypatch.setattr(
        guide_audio_module.GuideAudioService,
        "request_audio_generation",
        lambda *_args, **_kwargs: pytest.fail("GET requested audio generation"),
    )
    monkeypatch.setattr(
        guide_audio_module.GuideAudioService,
        "retry_audio_generation",
        lambda *_args, **_kwargs: pytest.fail("GET retried audio generation"),
    )

    failed_response = client.get(f"/api/v1/plans/{plan.id}/guide", headers=auth_headers(app, 1))
    failed_guide = failed_response.get_json()["data"]["guide"]
    db.session.refresh(guide)

    assert failed_response.status_code == 200
    assert failed_guide["audioStatus"] == "ready"
    assert failed_guide["audioUrl"] is None
    assert failed_guide["narrationText"]
    assert failed_guide["childIntro"]
    assert failed_guide["questions"]
    assert failed_guide["focusItems"]
    assert snapshot == (
        guide.audio_status,
        guide.audio_object_key,
        guide.audio_source_hash,
        guide.audio_duration_sec,
    )

    storage.signing_error = None
    recovered_response = client.get(f"/api/v1/plans/{plan.id}/guide", headers=auth_headers(app, 1))
    recovered_guide = recovered_response.get_json()["data"]["guide"]

    assert recovered_response.status_code == 200
    assert recovered_guide["audioStatus"] == "ready"
    assert recovered_guide["audioUrl"].startswith("https://signed.example.test/")


def test_get_guide_degrades_ready_audio_when_storage_is_not_configured(audio_db, app, client):
    _user, plan, guide = create_audio_fixture()
    guide.audio_status = "ready"
    guide.audio_object_key = "guide-audio/500/current.mp3"
    guide.narration_text = narration_builder()(plan=plan, guide=guide)
    guide.audio_source_hash = source_hash(
        narration_text=guide.narration_text,
        language="zh-CN",
        voice_profile_id="warm-guide-v1",
        tts_config_version="p8-2b2-edge-v1",
        output_format="mp3",
    )
    guide.audio_duration_sec = 97
    db.session.commit()

    response = client.get(f"/api/v1/plans/{plan.id}/guide", headers=auth_headers(app, 1))
    guide_payload = response.get_json()["data"]["guide"]

    assert response.status_code == 200
    assert guide_payload["audioStatus"] == "ready"
    assert guide_payload["audioUrl"] is None


def test_get_guide_never_returns_signed_url_for_non_ready_audio(audio_db, app, client):
    _user, plan, guide = create_audio_fixture()
    guide.audio_status = "failed"
    guide.audio_object_key = "guide-audio/500/old.mp3"
    guide.audio_url = "https://database.example.test/old.mp3"
    db.session.commit()

    response = client.get(f"/api/v1/plans/{plan.id}/guide", headers=auth_headers(app, 1))
    guide_payload = response.get_json()["data"]["guide"]

    assert response.status_code == 200
    assert guide_payload["audioStatus"] == "failed"
    assert guide_payload["audioUrl"] is None


def test_other_user_cannot_read_audio_status_or_retry_audio(audio_db, app, client):
    create_audio_fixture()
    other_user = User(id=2, phone="13800000002", nickname="其他用户")
    db.session.add(other_user)
    db.session.commit()

    get_response = client.get("/api/v1/plans/100/guide", headers=auth_headers(app, 2))
    retry_response = client.post("/api/v1/plans/100/guide/audio/retry", headers=auth_headers(app, 2))

    assert get_response.status_code == 404
    assert get_response.get_json()["error"]["code"] == "PLAN_NOT_FOUND"
    assert retry_response.status_code == 404
    assert retry_response.get_json()["error"]["code"] == "PLAN_NOT_FOUND"


def test_owner_audio_retry_endpoint_only_accepts_failed_audio(audio_db, app, client):
    create_audio_fixture()

    response = client.post("/api/v1/plans/100/guide/audio/retry", headers=auth_headers(app, 1))

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "AUDIO_RETRY_NOT_ALLOWED"


def test_explicit_audio_request_creates_exactly_one_current_audio_job_and_hides_job_details(audio_db, app, client):
    _user, plan, guide = create_audio_fixture()
    audio_job_model = ensure_audio_job_table()

    first = client.post(f"/api/v1/plans/{plan.id}/guide/audio/request", headers=auth_headers(app, 1))
    second = client.post(f"/api/v1/plans/{plan.id}/guide/audio/request", headers=auth_headers(app, 1))

    assert first.status_code == 202
    assert second.status_code == 202
    first_payload = first.get_json()["data"]
    second_payload = second.get_json()["data"]
    assert first_payload["audioStatus"] == "pending"
    assert first_payload["created"] is True
    assert second_payload["audioStatus"] == "pending"
    assert second_payload["created"] is False
    assert "jobStatus" in first_payload
    for forbidden in ("id", "providerJobId", "generationToken", "objectKey", "sourceHash", "guideId"):
        assert forbidden not in first_payload

    jobs = audio_job_model.query.all()
    db.session.refresh(guide)
    assert len(jobs) == 1
    assert jobs[0].guide_id == guide.id
    assert jobs[0].guide_version == guide.guide_version
    assert jobs[0].source_hash == guide.audio_source_hash
    assert jobs[0].generation_token == guide.audio_generation_token
    assert guide.audio_status == "pending"


def test_audio_request_rolls_back_generation_intent_when_audio_job_insert_fails(audio_db, app, client):
    _user, plan, guide = create_audio_fixture()
    audio_job_model = ensure_audio_job_table()
    db.session.execute(
        text(
            "CREATE TRIGGER fail_guide_audio_job_insert "
            "BEFORE INSERT ON guide_audio_jobs "
            "BEGIN SELECT RAISE(ABORT, 'forced audio job failure'); END"
        )
    )
    db.session.commit()

    response = client.post(f"/api/v1/plans/{plan.id}/guide/audio/request", headers=auth_headers(app, 1))

    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "DATABASE_ERROR"
    db.session.refresh(guide)
    assert guide.audio_status == "none"
    assert guide.audio_source_hash is None
    assert guide.audio_generation_token is None
    assert audio_job_model.query.count() == 0


def test_explicit_audio_request_does_not_generate_missing_guide_or_job(audio_db, app, client):
    user = User(id=1, phone="13800000001", nickname="童旅用户")
    child = Child(
        id=10,
        user_id=1,
        name="小小探索家",
        age=7,
        age_group="7-12",
        interests=[],
        is_default=True,
    )
    plan = ExplorationPlan(
        id=100,
        user_id=1,
        child_id=10,
        title="故宫亲子探索",
        destination="故宫博物院",
        age_group="7-12",
        duration="3小时",
        interests=[],
        status="ready",
    )
    db.session.add_all([user, child, plan])
    db.session.commit()
    audio_job_model = ensure_audio_job_table()

    response = client.post("/api/v1/plans/100/guide/audio/request", headers=auth_headers(app, 1))

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "GUIDE_NOT_FOUND"
    assert GuideCard.query.count() == 0
    assert audio_job_model.query.count() == 0


def test_explicit_audio_request_rejects_missing_narration_without_creating_job(audio_db, app, client):
    _user, plan, guide = create_audio_fixture()
    guide.child_intro = []
    guide.questions = []
    guide.focus_items = []
    guide.narration_text = None
    db.session.commit()
    audio_job_model = ensure_audio_job_table()

    response = client.post(f"/api/v1/plans/{plan.id}/guide/audio/request", headers=auth_headers(app, 1))

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "NARRATION_CONTENT_INSUFFICIENT"
    db.session.refresh(guide)
    assert guide.audio_status == "none"
    assert audio_job_model.query.count() == 0


def test_other_user_cannot_request_audio_or_observe_audio_job(audio_db, app, client):
    create_audio_fixture()
    other_user = User(id=2, phone="13800000002", nickname="其他用户")
    db.session.add(other_user)
    db.session.commit()
    audio_job_model = ensure_audio_job_table()

    response = client.post("/api/v1/plans/100/guide/audio/request", headers=auth_headers(app, 2))

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "PLAN_NOT_FOUND"
    assert audio_job_model.query.count() == 0
