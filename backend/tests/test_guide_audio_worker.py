from datetime import timedelta
import importlib

import pytest

from app import create_app
from app.extensions import db
from app.models import Child, ExplorationPlan, GuideCard, User


def require_module(module_name):
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        pytest.fail(f"P8.2B2 worker contract is missing: {module_name} ({error})")


def minimal_valid_mp3_bytes(frame_count=40):
    frame = b"\xff\xfb\x90\x00" + (b"\x00" * 413)
    return frame * frame_count


@pytest.fixture()
def worker_app():
    return create_app("testing")


@pytest.fixture()
def worker_db(worker_app):
    with worker_app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def create_pending_generation():
    job_model = require_module("app.models.guide_audio_job").GuideAudioJob
    user = User(id=1, phone="13800000001", nickname="童旅用户")
    child = Child(
        id=10,
        user_id=1,
        name="小小探索家",
        age=7,
        age_group="7-12",
        interests=["建筑"],
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
        interests=["建筑"],
        status="ready",
    )
    guide = GuideCard(
        id=500,
        plan_id=100,
        child_intro=["一起看看屋顶上的小兽吧。"],
        questions=["你发现了什么？"],
        focus_items=["屋顶"],
        narration_text="我们现在来到故宫博物院，一起看看屋顶上的小兽吧。",
        audio_status="pending",
        audio_source_hash="a" * 64,
        audio_generation_token="token-v1",
    )
    job = job_model(
        guide_id=500,
        guide_version=1,
        source_hash="a" * 64,
        generation_token="token-v1",
        status="queued",
        attempt_count=0,
        available_at=require_module("app.services.guide_audio_jobs").utc_now(),
    )
    db.session.add_all([user, child, plan, guide, job])
    db.session.commit()
    return guide, job


class RecordingStorage:
    def __init__(self, *, after_put=None):
        self.after_put = after_put
        self.put_calls = []
        self.deleted = []

    def put(self, *, object_key, audio_bytes, content_type):
        self.put_calls.append((object_key, audio_bytes, content_type))
        if self.after_put is not None:
            self.after_put()
        return object_key

    def delete(self, *, object_key):
        self.deleted.append(object_key)

    def create_signed_url(self, *, object_key, expires_in_seconds):
        return f"https://signed.example.test/{object_key}?expires={expires_in_seconds}"


def test_worker_run_once_is_a_bounded_cli_unit_of_work(worker_db):
    worker_module = require_module("app.workers.guide_audio_worker")

    assert callable(worker_module.run_once)
    assert callable(worker_module.run_forever)


def test_worker_idle_run_once_ends_claim_transaction(worker_db):
    worker_module = require_module("app.workers.guide_audio_worker")

    result = worker_module.run_once(tts_provider=object(), storage=object())

    assert result.status == "idle"
    assert db.session().in_transaction() is False


def test_worker_idle_iteration_ends_claim_transaction_before_sleep(worker_db, monkeypatch):
    worker_module = require_module("app.workers.guide_audio_worker")
    transactions_at_sleep = []

    def stop_after_first_sleep(_seconds):
        transactions_at_sleep.append(db.session().in_transaction())
        raise StopIteration

    monkeypatch.setattr(worker_module.time, "sleep", stop_after_first_sleep)

    with pytest.raises(StopIteration):
        worker_module.run_forever(tts_provider=object(), storage=object(), poll_seconds=1)

    assert transactions_at_sleep == [False]


def test_worker_iteration_releases_session_when_run_once_raises(worker_db, monkeypatch):
    worker_module = require_module("app.workers.guide_audio_worker")

    def failed_run_once(**_kwargs):
        GuideCard.query.first()
        assert db.session().in_transaction() is True
        raise RuntimeError("database failure")

    monkeypatch.setattr(worker_module, "run_once", failed_run_once)

    with pytest.raises(RuntimeError, match="database failure"):
        worker_module.run_forever(tts_provider=object(), storage=object(), poll_seconds=1)

    assert db.session().in_transaction() is False


def test_worker_completes_direct_ready_provider_result_and_marks_current_guide_ready(worker_db):
    worker_module = require_module("app.workers.guide_audio_worker")
    tts_module = require_module("app.services.tts_provider")
    jobs_module = require_module("app.services.guide_audio_jobs")
    guide, job = create_pending_generation()
    now = jobs_module.utc_now()

    class DirectReadyProvider:
        def submit(self, request):
            return tts_module.TTSJobResult(
                status="ready",
                audio_bytes=minimal_valid_mp3_bytes(),
                content_type="audio/mpeg",
            )

        def poll(self, provider_job_id):
            pytest.fail("direct-ready generation must not poll")

        def fetch(self, provider_job_id):
            pytest.fail("direct-ready generation must not fetch")

    storage = RecordingStorage()
    result = worker_module.run_once(
        tts_provider=DirectReadyProvider(),
        storage=storage,
        now=now,
    )
    db.session.refresh(guide)
    db.session.refresh(job)

    assert result.status == "completed"
    assert guide.audio_status == "ready"
    assert guide.audio_duration_sec == 1
    assert guide.audio_object_key == f"guide-audio/500/{'a' * 64}/token-v1.mp3"
    assert job.status == "completed"
    assert job.finished_at is not None
    assert len(storage.put_calls) == 1


def test_worker_persists_provider_pending_without_holding_claim_and_later_polls(worker_db):
    worker_module = require_module("app.workers.guide_audio_worker")
    tts_module = require_module("app.services.tts_provider")
    jobs_module = require_module("app.services.guide_audio_jobs")
    guide, job = create_pending_generation()
    now = jobs_module.utc_now()

    class PendingProvider:
        def __init__(self):
            self.submit_calls = 0
            self.poll_calls = 0
            self.fetch_calls = 0

        def submit(self, request):
            self.submit_calls += 1
            return tts_module.TTSJobResult(status="provider_pending", provider_job_id="vendor-job-1")

        def poll(self, provider_job_id):
            self.poll_calls += 1
            assert provider_job_id == "vendor-job-1"
            return tts_module.TTSJobResult(status="ready", provider_job_id=provider_job_id)

        def fetch(self, provider_job_id):
            self.fetch_calls += 1
            assert provider_job_id == "vendor-job-1"
            return tts_module.SynthesisResult(
                audio_bytes=minimal_valid_mp3_bytes(),
                content_type="audio/mpeg",
                duration_sec=999,
            )

    provider = PendingProvider()
    storage = RecordingStorage()
    first = worker_module.run_once(tts_provider=provider, storage=storage, now=now)
    db.session.refresh(job)

    assert first.status == "provider_pending"
    assert job.status == "provider_pending"
    assert job.provider_job_id == "vendor-job-1"
    assert job.available_at > now
    assert job.lease_expires_at is None
    assert provider.submit_calls == 1

    second = worker_module.run_once(tts_provider=provider, storage=storage, now=job.available_at)
    db.session.refresh(guide)
    db.session.refresh(job)

    assert second.status == "completed"
    assert provider.submit_calls == 1
    assert provider.poll_calls == 1
    assert provider.fetch_calls == 1
    assert guide.audio_status == "ready"
    assert job.status == "completed"


def test_worker_retries_only_transient_errors_with_bounded_backoff(worker_db):
    worker_module = require_module("app.workers.guide_audio_worker")
    tts_module = require_module("app.services.tts_provider")
    jobs_module = require_module("app.services.guide_audio_jobs")
    guide, job = create_pending_generation()
    now = jobs_module.utc_now()

    class TimeoutProvider:
        def submit(self, request):
            raise tts_module.TTSProviderError("TTS_TIMEOUT", "timeout", retryable=True)

    storage = RecordingStorage()
    first = worker_module.run_once(tts_provider=TimeoutProvider(), storage=storage, now=now)
    db.session.refresh(job)
    assert first.status == "queued"
    assert job.status == "queued"
    assert job.attempt_count == 1
    assert job.available_at == now + timedelta(seconds=30)

    second = worker_module.run_once(tts_provider=TimeoutProvider(), storage=storage, now=job.available_at)
    db.session.refresh(job)
    assert second.status == "queued"
    assert job.attempt_count == 2
    assert job.available_at == now + timedelta(seconds=150)

    third = worker_module.run_once(tts_provider=TimeoutProvider(), storage=storage, now=job.available_at)
    db.session.refresh(guide)
    db.session.refresh(job)
    assert third.status == "failed"
    assert job.status == "failed"
    assert job.last_error_code == "TTS_TIMEOUT"
    assert guide.audio_status == "failed"


def test_worker_logs_provider_diagnostic_without_persisting_it(worker_db, caplog):
    worker_module = require_module("app.workers.guide_audio_worker")
    tts_module = require_module("app.services.tts_provider")
    jobs_module = require_module("app.services.guide_audio_jobs")
    guide, job = create_pending_generation()

    class BadRequestProvider:
        def submit(self, request):
            raise tts_module.TTSProviderError(
                "TTS_BAD_REQUEST",
                "Edge TTS rejected the request",
                retryable=False,
                diagnostic_detail="Invalid voice parameter",
            )

    with caplog.at_level("WARNING", logger=worker_module.__name__):
        result = worker_module.run_once(
            tts_provider=BadRequestProvider(),
            storage=RecordingStorage(),
            now=jobs_module.utc_now(),
        )
    db.session.refresh(guide)
    db.session.refresh(job)

    assert result.status == "failed"
    assert job.last_error_code == "TTS_BAD_REQUEST"
    assert guide.audio_error_code == "TTS_BAD_REQUEST"
    assert "guide_audio_tts_error" in caplog.text
    assert f"job_id={job.id}" in caplog.text
    assert f"guide_id={guide.id}" in caplog.text
    assert "error_code=TTS_BAD_REQUEST" in caplog.text
    assert "retryable=False" in caplog.text
    assert "provider_detail='Invalid voice parameter'" in caplog.text


def test_worker_marks_stale_and_cleans_uploaded_v1_object_without_touching_v2_guide(worker_db):
    worker_module = require_module("app.workers.guide_audio_worker")
    tts_module = require_module("app.services.tts_provider")
    jobs_module = require_module("app.services.guide_audio_jobs")
    guide, job = create_pending_generation()

    class DirectReadyProvider:
        def submit(self, request):
            return tts_module.TTSJobResult(
                status="ready",
                audio_bytes=minimal_valid_mp3_bytes(),
                content_type="audio/mpeg",
            )

    def switch_guide_to_v2():
        guide.guide_version = 2
        guide.audio_status = "pending"
        guide.audio_source_hash = "b" * 64
        guide.audio_generation_token = "token-v2"
        guide.audio_object_key = f"guide-audio/500/{'b' * 64}/token-v2.mp3"
        db.session.commit()

    storage = RecordingStorage(after_put=switch_guide_to_v2)
    result = worker_module.run_once(
        tts_provider=DirectReadyProvider(),
        storage=storage,
        now=jobs_module.utc_now(),
    )
    db.session.refresh(guide)
    db.session.refresh(job)

    assert result.status == "stale"
    assert job.status == "stale"
    assert guide.guide_version == 2
    assert guide.audio_status == "pending"
    assert guide.audio_source_hash == "b" * 64
    assert guide.audio_generation_token == "token-v2"
    assert guide.audio_object_key == f"guide-audio/500/{'b' * 64}/token-v2.mp3"
    assert job.last_error_code is None
    assert storage.deleted == [f"guide-audio/500/{'a' * 64}/token-v1.mp3"]


def test_worker_records_controlled_cleanup_error_without_touching_v2_guide(worker_db):
    worker_module = require_module("app.workers.guide_audio_worker")
    tts_module = require_module("app.services.tts_provider")
    storage_module = require_module("app.services.audio_storage")
    jobs_module = require_module("app.services.guide_audio_jobs")
    guide, job = create_pending_generation()

    class DirectReadyProvider:
        def __init__(self):
            self.submit_calls = 0

        def submit(self, request):
            self.submit_calls += 1
            return tts_module.TTSJobResult(
                status="ready",
                audio_bytes=minimal_valid_mp3_bytes(),
                content_type="audio/mpeg",
            )

    def switch_guide_to_v2():
        guide.guide_version = 2
        guide.audio_status = "ready"
        guide.audio_source_hash = "b" * 64
        guide.audio_generation_token = "token-v2"
        guide.audio_object_key = f"guide-audio/500/{'b' * 64}/token-v2.mp3"
        db.session.commit()

    class CleanupFailingStorage(RecordingStorage):
        def delete(self, *, object_key):
            self.deleted.append(object_key)
            raise storage_module.AudioStorageError(
                "AUDIO_STORAGE_ACCESS_DENIED",
                "private-bucket/path/to/v1.mp3",
            )

    provider = DirectReadyProvider()
    storage = CleanupFailingStorage(after_put=switch_guide_to_v2)
    result = worker_module.run_once(
        tts_provider=provider,
        storage=storage,
        now=jobs_module.utc_now(),
    )
    db.session.refresh(guide)
    db.session.refresh(job)

    assert result.status == "stale"
    assert job.status == "stale"
    assert job.last_error_code == "STALE_CLEANUP_FAILED"
    assert guide.guide_version == 2
    assert guide.audio_status == "ready"
    assert guide.audio_source_hash == "b" * 64
    assert guide.audio_generation_token == "token-v2"
    assert guide.audio_object_key == f"guide-audio/500/{'b' * 64}/token-v2.mp3"
    assert storage.deleted == [f"guide-audio/500/{'a' * 64}/token-v1.mp3"]
    assert len(storage.put_calls) == 1
    assert provider.submit_calls == 1


def test_stale_job_failure_never_marks_new_generation_failed(worker_db):
    worker_module = require_module("app.workers.guide_audio_worker")
    tts_module = require_module("app.services.tts_provider")
    jobs_module = require_module("app.services.guide_audio_jobs")
    guide, job = create_pending_generation()

    class StalingPermanentFailureProvider:
        def submit(self, request):
            guide.guide_version = 2
            guide.audio_status = "pending"
            guide.audio_source_hash = "b" * 64
            guide.audio_generation_token = "token-v2"
            db.session.commit()
            raise tts_module.TTSProviderError("TTS_BAD_REQUEST", "bad request", retryable=False)

    result = worker_module.run_once(
        tts_provider=StalingPermanentFailureProvider(),
        storage=RecordingStorage(),
        now=jobs_module.utc_now(),
    )
    db.session.refresh(guide)
    db.session.refresh(job)

    assert result.status == "stale"
    assert job.status == "stale"
    assert guide.audio_status == "pending"
    assert guide.audio_generation_token == "token-v2"
