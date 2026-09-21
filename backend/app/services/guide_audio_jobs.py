from datetime import timedelta

from sqlalchemy import and_, or_

from app.extensions import db
from app.models import GuideAudioJob
from app.utils.time import utc_now


DEFAULT_LEASE_SECONDS = 60
MAX_AUDIO_ATTEMPTS = 3
RETRY_DELAYS_SECONDS = (30, 120, 600)
PROVIDER_POLL_DELAY_SECONDS = 30


def generation_is_current(guide, job):
    return (
        guide is not None
        and guide.id == job.guide_id
        and guide.guide_version == job.guide_version
        and guide.audio_source_hash == job.source_hash
        and guide.audio_generation_token == job.generation_token
    )


def audio_object_key(job):
    return f"guide-audio/{job.guide_id}/{job.source_hash}/{job.generation_token}.mp3"


class AudioJobService:
    def __init__(self, *, lease_seconds=DEFAULT_LEASE_SECONDS):
        self.lease_seconds = lease_seconds

    def create_or_reuse(self, intent, *, now=None, phase_callback=None):
        now = now or utc_now()
        criteria = {
            "guide_id": intent.guide_id,
            "guide_version": intent.guide_version,
            "source_hash": intent.source_hash,
            "generation_token": intent.generation_token,
        }
        if phase_callback is not None:
            phase_callback("existing_job_lookup")
        existing = GuideAudioJob.query.filter_by(**criteria).with_for_update().first()
        if existing is not None:
            return existing, False

        job = GuideAudioJob(
            **criteria,
            status="queued",
            attempt_count=0,
            available_at=now,
        )
        db.session.add(job)
        if phase_callback is not None:
            phase_callback("job_insert_flush")
        db.session.flush()
        return job, True

    def _claimable_filter(self, now):
        return or_(
            and_(GuideAudioJob.status == "queued", GuideAudioJob.available_at <= now),
            and_(GuideAudioJob.status == "claimed", GuideAudioJob.lease_expires_at <= now),
            and_(GuideAudioJob.status == "provider_pending", GuideAudioJob.available_at <= now),
        )

    def claim_next_audio_job(self, *, now=None):
        now = now or utc_now()
        job = (
            GuideAudioJob.query.filter(self._claimable_filter(now))
            .order_by(GuideAudioJob.available_at.asc(), GuideAudioJob.id.asc())
            .with_for_update(skip_locked=True)
            .first()
        )
        if job is None:
            db.session.rollback()
            return None

        prior_status = job.status
        job.status = "claimed"
        job.claimed_at = now
        job.lease_expires_at = now + timedelta(seconds=self.lease_seconds)
        if prior_status != "provider_pending":
            job.attempt_count += 1
        db.session.commit()
        return job

    def mark_provider_pending(self, job, *, provider_job_id, available_at):
        job = GuideAudioJob.query.filter_by(id=job.id).with_for_update().first()
        if job is None:
            db.session.rollback()
            return None
        job.status = "provider_pending"
        job.provider_job_id = provider_job_id
        job.available_at = available_at
        job.claimed_at = None
        job.lease_expires_at = None
        db.session.commit()
        return job

    def mark_stale(self, job, *, now=None):
        job = GuideAudioJob.query.filter_by(id=job.id).with_for_update().first()
        if job is None:
            db.session.rollback()
            return None
        job.status = "stale"
        job.claimed_at = None
        job.lease_expires_at = None
        job.finished_at = now or utc_now()
        db.session.commit()
        return job

    def schedule_retry(self, job, *, error_code, now=None, retry_after_seconds=None):
        now = now or utc_now()
        job = GuideAudioJob.query.filter_by(id=job.id).with_for_update().first()
        if job is None:
            db.session.rollback()
            return None

        attempt_index = max(0, min(job.attempt_count - 1, len(RETRY_DELAYS_SECONDS) - 1))
        delay = RETRY_DELAYS_SECONDS[attempt_index]
        if isinstance(retry_after_seconds, int) and retry_after_seconds > 0:
            delay = min(retry_after_seconds, RETRY_DELAYS_SECONDS[-1])
        job.status = "queued"
        job.available_at = now + timedelta(seconds=delay)
        job.claimed_at = None
        job.lease_expires_at = None
        job.last_error_code = error_code
        db.session.commit()
        return job

    def mark_completed(self, job, *, now=None):
        job = GuideAudioJob.query.filter_by(id=job.id).with_for_update().first()
        if job is None:
            db.session.rollback()
            return None
        job.status = "completed"
        job.claimed_at = None
        job.lease_expires_at = None
        job.finished_at = now or utc_now()
        job.last_error_code = None
        db.session.commit()
        return job

    def mark_failed(self, job, *, error_code, now=None):
        job = GuideAudioJob.query.filter_by(id=job.id).with_for_update().first()
        if job is None:
            db.session.rollback()
            return None
        job.status = "failed"
        job.claimed_at = None
        job.lease_expires_at = None
        job.finished_at = now or utc_now()
        job.last_error_code = error_code
        db.session.commit()
        return job
