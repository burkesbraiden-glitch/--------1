from app.extensions import db
from app.utils.time import utc_now


AUDIO_JOB_STATUSES = {
    "queued",
    "claimed",
    "provider_pending",
    "completed",
    "failed",
    "stale",
}


class GuideAudioJob(db.Model):
    __tablename__ = "guide_audio_jobs"
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('queued', 'claimed', 'provider_pending', 'completed', 'failed', 'stale')",
            name="ck_guide_audio_jobs_status_allowed",
        ),
        db.UniqueConstraint(
            "guide_id",
            "guide_version",
            "source_hash",
            "generation_token",
            name="uq_guide_audio_jobs_generation",
        ),
        db.Index(
            "ix_guide_audio_jobs_status_available_id",
            "status",
            "available_at",
            "id",
        ),
    )

    id = db.Column(db.BigInteger().with_variant(db.Integer, "sqlite"), primary_key=True)
    guide_id = db.Column(
        db.BigInteger,
        db.ForeignKey("guide_cards.id", ondelete="CASCADE"),
        nullable=False,
    )
    guide_version = db.Column(db.Integer, nullable=False)
    source_hash = db.Column(db.String(64), nullable=False)
    generation_token = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(24), nullable=False, default="queued", server_default="queued")
    attempt_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    available_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    claimed_at = db.Column(db.DateTime, nullable=True)
    lease_expires_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    provider_job_id = db.Column(db.String(255), nullable=True)
    last_error_code = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    guide = db.relationship("GuideCard")
