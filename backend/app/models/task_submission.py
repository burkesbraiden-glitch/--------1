from app.extensions import db
from app.utils.time import utc_now


class TaskSubmission(db.Model):
    __tablename__ = "task_submissions"
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('in-progress', 'completed')",
            name="status_allowed",
        ),
    )

    id = db.Column(db.BigInteger, primary_key=True)
    task_id = db.Column(
        db.BigInteger,
        db.ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    status = db.Column(db.String(24), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    note = db.Column(db.Text, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    task = db.relationship("Task", back_populates="submission")
