from app.extensions import db
from app.utils.time import utc_now


class JourneyRecord(db.Model):
    __tablename__ = "journey_records"
    __table_args__ = (
        db.UniqueConstraint("plan_id", name="plan_journey_record"),
        db.CheckConstraint(
            "status IN ('draft', 'finalized')",
            name="status_allowed",
        ),
    )

    id = db.Column(db.BigInteger, primary_key=True)
    plan_id = db.Column(
        db.BigInteger,
        db.ForeignKey("exploration_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    custom_title = db.Column(db.String(120), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    cover_submission_id = db.Column(
        db.BigInteger,
        db.ForeignKey("task_submissions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = db.Column(db.String(24), nullable=False, default="draft", server_default="draft")
    finalized_at = db.Column(db.DateTime, nullable=True)
    snapshot = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    plan = db.relationship("ExplorationPlan", back_populates="journey_record")
    cover_submission = db.relationship("TaskSubmission", foreign_keys=[cover_submission_id])
