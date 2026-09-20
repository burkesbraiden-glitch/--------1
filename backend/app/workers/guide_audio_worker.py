from dataclasses import dataclass
from datetime import timedelta
import time

from app import create_app
from app.extensions import db
from app.models import GuideAudioJob, GuideCard
from app.services.audio_storage import AudioStorageError, UnconfiguredAudioStorage
from app.services.audio_validation import AudioValidationError, validate_generated_audio
from app.services.guide_audio import (
    AUDIO_LANGUAGE,
    AUDIO_OUTPUT_FORMAT,
    AUDIO_VOICE_PROFILE_ID,
)
from app.services.guide_audio_jobs import (
    MAX_AUDIO_ATTEMPTS,
    PROVIDER_POLL_DELAY_SECONDS,
    AudioJobService,
    audio_object_key,
    generation_is_current,
)
from app.services.tts_provider import TTSJobResult, TTSProviderError, TTSRequest, UnconfiguredTTSProvider
from app.utils.time import utc_now


@dataclass(frozen=True)
class WorkerRunResult:
    status: str


def _current_guide_for_job(job):
    guide = GuideCard.query.filter_by(id=job.guide_id).with_for_update().first()
    if guide is None or not generation_is_current(guide, job):
        return None
    return guide


def _mark_current_guide_generating(job):
    guide = _current_guide_for_job(job)
    if guide is None:
        db.session.rollback()
        return False
    if guide.audio_status == "pending":
        guide.audio_status = "generating"
        guide.audio_error_code = None
        db.session.commit()
    else:
        db.session.rollback()
    return guide.audio_status == "generating"


def _mark_stale(job, *, now, cleanup_error_code=None):
    job_row = GuideAudioJob.query.filter_by(id=job.id).with_for_update().first()
    if (
        job_row is None
        or job_row.status != "claimed"
        or job_row.guide_id != job.guide_id
        or job_row.guide_version != job.guide_version
        or job_row.source_hash != job.source_hash
        or job_row.generation_token != job.generation_token
    ):
        db.session.rollback()
        return WorkerRunResult(status="stale")
    job_row.status = "stale"
    job_row.claimed_at = None
    job_row.lease_expires_at = None
    job_row.finished_at = now
    if cleanup_error_code is not None:
        job_row.last_error_code = cleanup_error_code
    db.session.commit()
    return WorkerRunResult(status="stale")


def _schedule_retry_or_fail(job, *, error, now):
    job_row = GuideAudioJob.query.filter_by(id=job.id).with_for_update().first()
    guide = _current_guide_for_job(job_row) if job_row is not None else None
    if job_row is None or guide is None:
        db.session.rollback()
        return _mark_stale(job, now=now)

    if error.retryable and job_row.attempt_count < MAX_AUDIO_ATTEMPTS:
        retry_after_seconds = getattr(error, "retry_after_seconds", None)
        AudioJobService().schedule_retry(
            job_row,
            error_code=error.code,
            now=now,
            retry_after_seconds=retry_after_seconds,
        )
        guide = GuideCard.query.filter_by(id=job.guide_id).with_for_update().first()
        if guide is None or not generation_is_current(guide, job):
            db.session.rollback()
            return _mark_stale(job, now=now)
        guide.audio_status = "pending"
        guide.audio_error_code = None
        db.session.commit()
        return WorkerRunResult(status="queued")

    job_row.status = "failed"
    job_row.claimed_at = None
    job_row.lease_expires_at = None
    job_row.finished_at = now
    job_row.last_error_code = error.code
    guide.audio_status = "failed"
    guide.audio_object_key = None
    guide.audio_duration_sec = None
    guide.audio_generated_at = None
    guide.audio_error_code = error.code
    db.session.commit()
    return WorkerRunResult(status="failed")


def _mark_ready_or_stale(job, *, persisted_key, duration_sec, now):
    job_row = GuideAudioJob.query.filter_by(id=job.id).with_for_update().first()
    guide = _current_guide_for_job(job_row) if job_row is not None else None
    if job_row is None or guide is None:
        db.session.rollback()
        return False

    guide.audio_status = "ready"
    guide.audio_object_key = persisted_key
    guide.audio_duration_sec = duration_sec
    guide.audio_generated_at = now
    guide.audio_error_code = None
    job_row.status = "completed"
    job_row.claimed_at = None
    job_row.lease_expires_at = None
    job_row.finished_at = now
    job_row.last_error_code = None
    db.session.commit()
    return True


def _provider_result_for_job(*, job, guide, tts_provider):
    if job.provider_job_id:
        result = tts_provider.poll(job.provider_job_id)
    else:
        result = tts_provider.submit(
            TTSRequest(
                text=guide.narration_text,
                language=AUDIO_LANGUAGE,
                voice=AUDIO_VOICE_PROFILE_ID,
                format=AUDIO_OUTPUT_FORMAT,
            )
        )
    if not isinstance(result, TTSJobResult):
        raise TTSProviderError("TTS_PROVIDER_RESULT_INVALID", "Provider returned an invalid result")
    return result


def _fetch_audio_if_ready(*, job, result, tts_provider):
    if result.audio_bytes is not None:
        return result.audio_bytes
    provider_job_id = result.provider_job_id or job.provider_job_id
    if not provider_job_id:
        raise TTSProviderError("TTS_PROVIDER_RESULT_INVALID", "Ready provider result has no audio")
    synthesis = tts_provider.fetch(provider_job_id)
    audio_bytes = getattr(synthesis, "audio_bytes", None)
    if not isinstance(audio_bytes, bytes):
        raise TTSProviderError("TTS_PROVIDER_RESULT_INVALID", "Provider fetch returned invalid audio")
    return audio_bytes


def _cleanup_stale_object(storage, *, object_key):
    try:
        storage.delete(object_key=object_key)
    except AudioStorageError:
        # The stale object is never linked from the current Guide. Storage lifecycle
        # cleanup can reconcile a temporary delete failure without touching V2.
        return "STALE_CLEANUP_FAILED"
    return None


def run_once(*, tts_provider=None, storage=None, now=None):
    """Claim and process at most one durable Guide audio job."""
    now = now or utc_now()
    tts_provider = tts_provider or UnconfiguredTTSProvider()
    storage = storage or UnconfiguredAudioStorage()
    job_service = AudioJobService()
    job = job_service.claim_next_audio_job(now=now)
    if job is None:
        return WorkerRunResult(status="idle")

    if not _mark_current_guide_generating(job):
        return _mark_stale(job, now=now)

    guide = _current_guide_for_job(job)
    if guide is None:
        return _mark_stale(job, now=now)
    db.session.rollback()

    try:
        provider_result = _provider_result_for_job(job=job, guide=guide, tts_provider=tts_provider)
    except TTSProviderError as error:
        return _schedule_retry_or_fail(job, error=error, now=now)

    if provider_result.status == "provider_pending":
        provider_job_id = provider_result.provider_job_id or job.provider_job_id
        if not provider_job_id:
            return _schedule_retry_or_fail(
                job,
                error=TTSProviderError("TTS_PROVIDER_RESULT_INVALID", "Pending provider result has no job ID"),
                now=now,
            )
        job_service.mark_provider_pending(
            job,
            provider_job_id=provider_job_id,
            available_at=now + timedelta(seconds=PROVIDER_POLL_DELAY_SECONDS),
        )
        return WorkerRunResult(status="provider_pending")

    if provider_result.status != "ready":
        return _schedule_retry_or_fail(
            job,
            error=TTSProviderError("TTS_PROVIDER_RESULT_INVALID", "Provider returned an unknown status"),
            now=now,
        )

    try:
        audio_bytes = _fetch_audio_if_ready(job=job, result=provider_result, tts_provider=tts_provider)
        validated_audio = validate_generated_audio(audio_bytes)
    except TTSProviderError as error:
        return _schedule_retry_or_fail(job, error=error, now=now)
    except AudioValidationError as error:
        return _schedule_retry_or_fail(
            job,
            error=TTSProviderError(error.code, error.message, retryable=False),
            now=now,
        )

    object_key = audio_object_key(job)
    try:
        persisted_key = storage.put(
            object_key=object_key,
            audio_bytes=validated_audio.audio_bytes,
            content_type=validated_audio.content_type,
        )
        if persisted_key != object_key:
            raise AudioStorageError("AUDIO_STORAGE_KEY_INVALID", "Storage returned an unexpected object key")
    except AudioStorageError as error:
        return _schedule_retry_or_fail(job, error=error, now=now)

    if not _mark_ready_or_stale(
        job,
        persisted_key=persisted_key,
        duration_sec=validated_audio.duration_sec,
        now=now,
    ):
        cleanup_error_code = _cleanup_stale_object(storage, object_key=persisted_key)
        return _mark_stale(job, now=now, cleanup_error_code=cleanup_error_code)
    return WorkerRunResult(status="completed")


def run_forever(*, tts_provider=None, storage=None, poll_seconds=1):
    while True:
        run_once(tts_provider=tts_provider, storage=storage)
        time.sleep(poll_seconds)


def main():
    app = create_app()
    poll_seconds = app.config.get("GUIDE_AUDIO_WORKER_POLL_SECONDS", 1)
    with app.app_context():
        run_forever(poll_seconds=poll_seconds)


if __name__ == "__main__":
    main()
