from app.extensions import db
from app.utils.time import utc_now


class ExplorationPlan(db.Model):
    __tablename__ = "exploration_plans"
    __table_args__ = (
        db.CheckConstraint("age_group IN ('3-6', '7-12')", name="age_group_allowed"),
        db.CheckConstraint(
            "status IN ('draft', 'ready', 'in-progress', 'completed')",
            name="status_allowed",
        ),
        db.UniqueConstraint("route_stop_id", "child_id", name="route_stop_child_unique"),
    )

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    child_id = db.Column(
        db.BigInteger,
        db.ForeignKey("children.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    route_stop_id = db.Column(
        db.BigInteger,
        db.ForeignKey("route_stops.id", ondelete="RESTRICT"),
        nullable=True,
    )
    title = db.Column(db.String(120), nullable=False)
    destination = db.Column(db.String(120), nullable=False)
    age_group = db.Column(db.String(16), nullable=False)
    duration = db.Column(db.String(32), nullable=False)
    interests = db.Column(db.JSON, nullable=False, default=list)
    source_snapshot = db.Column(db.JSON, nullable=True)
    status = db.Column(db.String(24), nullable=False, default="draft", server_default="draft")
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    user = db.relationship("User", back_populates="exploration_plans")
    child = db.relationship("Child", back_populates="exploration_plans")
    route_stop = db.relationship("RouteStop", back_populates="exploration_plans")
    guide_card = db.relationship(
        "GuideCard",
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    journey_record = db.relationship(
        "JourneyRecord",
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    tasks = db.relationship(
        "Task",
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
