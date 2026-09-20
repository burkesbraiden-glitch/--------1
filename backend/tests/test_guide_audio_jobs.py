from datetime import timedelta
import importlib

import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.extensions import db
from app.models import Child, ExplorationPlan, GuideCard, User


def require_module(module_name):
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        pytest.fail(f"P8.2B2 production contract is missing: {module_name} ({error})")


def require_audio_job_model():
    return require_module("app.models.guide_audio_job").GuideAudioJob


@pytest.fixture()
def jobs_app():
    return create_app("testing")


@pytest.fixture()
def jobs_db(jobs_app):
    with jobs_app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def create_job_fixture(*, status="queued", available_at=None):
    user = User(id=1, phone="13800000001", nickname="童旅用户")
    child = Child(
        id=10,
        user_id=1,
        name="小小探索家",
        age=7,
        age_group="7-12",
        interests=["历史故事"],
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
        interests=["历史故事"],
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
    job = require_audio_job_model()(
        guide_id=500,
        guide_version=1,
        source_hash="a" * 64,
        generation_token="token-v1",
        status=status,
        attempt_count=0,
        available_at=available_at,
    )
    db.session.add_all([user, child, plan, guide, job])
    db.session.commit()
    return user, plan, guide, job


def test_audio_job_model_has_execution_only_fields_and_queue_index(jobs_db):
    module = require_module("app.models.guide_audio_job")
    model = module.GuideAudioJob
    table = model.__table__

    assert set(module.AUDIO_JOB_STATUSES) == {
        "queued",
        "claimed",
        "provider_pending",
        "completed",
        "failed",
        "stale",
    }
    for field in (
        "id",
        "guide_id",
        "guide_version",
        "source_hash",
        "generation_token",
        "status",
        "attempt_count",
        "available_at",
        "claimed_at",
        "lease_expires_at",
        "finished_at",
        "provider_job_id",
        "last_error_code",
        "created_at",
        "updated_at",
    ):
        assert field in table.c

    unique_sets = {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("guide_id", "guide_version", "source_hash", "generation_token") in unique_sets
    assert any(tuple(index.columns.keys()) == ("status", "available_at", "id") for index in table.indexes)


def test_claim_next_audio_job_claims_only_due_queued_job_once(jobs_db):
    jobs_module = require_module("app.services.guide_audio_jobs")
    now = jobs_module.utc_now()
    _user, _plan, _guide, job = create_job_fixture(available_at=now)
    service = jobs_module.AudioJobService()

    claimed = service.claim_next_audio_job(now=now)
    db.session.refresh(job)

    assert claimed.id == job.id
    assert job.status == "claimed"
    assert job.claimed_at == now
    assert job.lease_expires_at > now
    assert job.attempt_count == 1
    assert service.claim_next_audio_job(now=now) is None


def test_claim_next_audio_job_does_not_claim_future_work_or_active_lease(jobs_db):
    jobs_module = require_module("app.services.guide_audio_jobs")
    now = jobs_module.utc_now()
    _user, _plan, _guide, job = create_job_fixture(available_at=now + timedelta(seconds=1))
    service = jobs_module.AudioJobService()

    assert service.claim_next_audio_job(now=now) is None

    job.available_at = now
    job.status = "claimed"
    job.claimed_at = now
    job.lease_expires_at = now + timedelta(seconds=30)
    db.session.commit()

    assert service.claim_next_audio_job(now=now + timedelta(seconds=1)) is None


def test_expired_lease_is_reclaimed_with_a_new_attempt(jobs_db):
    jobs_module = require_module("app.services.guide_audio_jobs")
    now = jobs_module.utc_now()
    _user, _plan, _guide, job = create_job_fixture(available_at=now)
    service = jobs_module.AudioJobService()

    first_claim = service.claim_next_audio_job(now=now)
    assert first_claim.id == job.id
    first_lease = job.lease_expires_at

    assert service.claim_next_audio_job(now=first_lease - timedelta(microseconds=1)) is None
    reclaimed = service.claim_next_audio_job(now=first_lease + timedelta(microseconds=1))
    db.session.refresh(job)

    assert reclaimed.id == job.id
    assert job.status == "claimed"
    assert job.attempt_count == 2
    assert job.claimed_at > now
    assert job.lease_expires_at > job.claimed_at


def test_production_audio_configuration_rejects_fake_unconfigured_and_missing_values():
    config_module = require_module("app.config")
    validate = config_module.validate_production_audio_config
    valid = {
        "APP_ENV": "production",
        "TTS_PROVIDER": "edge",
        "EDGE_TTS_BASE_URL": "https://edge-worker.example.test",
        "AUDIO_STORAGE_PROVIDER": "r2",
        "R2_ACCOUNT_ID": "account-id-123",
        "R2_ACCESS_KEY_ID": "access-key",
        "R2_SECRET_ACCESS_KEY": "secret-key",
        "R2_BUCKET": "test-private-bucket",
    }

    validate(valid)
    for key, value in (
        ("TTS_PROVIDER", "fake"),
        ("TTS_PROVIDER", "unconfigured"),
        ("AUDIO_STORAGE_PROVIDER", "fake"),
        ("AUDIO_STORAGE_PROVIDER", "unconfigured"),
        ("EDGE_TTS_BASE_URL", ""),
        ("R2_ACCOUNT_ID", ""),
        ("R2_ACCESS_KEY_ID", ""),
        ("R2_SECRET_ACCESS_KEY", ""),
        ("R2_BUCKET", ""),
    ):
        invalid = {**valid, key: value}
        with pytest.raises(RuntimeError, match="audio|Audio|TTS|storage"):
            validate(invalid)


def test_development_and_testing_may_explicitly_use_fake_audio_configuration():
    config_module = require_module("app.config")
    validate = config_module.validate_production_audio_config

    validate({"APP_ENV": "development", "TTS_PROVIDER": "fake", "AUDIO_STORAGE_PROVIDER": "fake"})
    validate({"APP_ENV": "testing", "TTS_PROVIDER": "fake", "AUDIO_STORAGE_PROVIDER": "fake"})


def test_audio_environment_example_documents_names_without_credentials():
    source = (importlib.import_module("pathlib").Path(__file__).resolve().parents[1] / ".env.example").read_text(
        encoding="utf-8"
    )

    for name in (
        "TTS_PROVIDER",
        "EDGE_TTS_BASE_URL",
        "EDGE_TTS_VOICE",
        "EDGE_TTS_SPEED",
        "EDGE_TTS_PITCH",
        "EDGE_TTS_STYLE",
        "EDGE_TTS_TIMEOUT_SECONDS",
        "AUDIO_STORAGE_PROVIDER",
        "R2_ACCOUNT_ID",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET",
        "AUDIO_SIGNED_URL_TTL_SECONDS",
        "GUIDE_AUDIO_WORKER_POLL_SECONDS",
    ):
        assert f"{name}=" in source
    assert "AKID" not in source
    assert "Authorization: Bearer" not in source


def test_edge_renderer_uses_a_new_tts_config_version_without_rewriting_source_hash_fields():
    guide_audio = require_module("app.services.guide_audio")

    assert guide_audio.TTS_CONFIG_VERSION == "p8-2b2-edge-v1"
