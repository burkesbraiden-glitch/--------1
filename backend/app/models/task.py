from app.extensions import db
from app.utils.time import utc_now


class Task(db.Model):
    __tablename__ = "tasks"
    __table_args__ = (
        db.UniqueConstraint("plan_id", "sort_order", name="plan_sort_order"),
        db.CheckConstraint("sort_order >= 1", name="sort_order_positive"),
        db.CheckConstraint("age_group IN ('3-6', '7-12')", name="age_group_allowed"),
    )

    id = db.Column(db.BigInteger, primary_key=True)
    plan_id = db.Column(
        db.BigInteger,
        db.ForeignKey("exploration_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sort_order = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(120), nullable=False)
    subtitle = db.Column(db.String(240), nullable=True)
    age_group = db.Column(db.String(16), nullable=False)
    duration = db.Column(db.String(32), nullable=False)
    task_type = db.Column(db.String(32), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    objective = db.Column(db.Text, nullable=False)
    steps = db.Column(db.JSON, nullable=False, default=list)
    questions = db.Column(db.JSON, nullable=False, default=list)
    record_mode = db.Column(db.String(255), nullable=False)
    theme = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    plan = db.relationship("ExplorationPlan", back_populates="tasks")
    submission = db.relationship(
        "TaskSubmission",
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
