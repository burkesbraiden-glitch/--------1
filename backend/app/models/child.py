from app.extensions import db
from app.utils.time import utc_now


class Child(db.Model):
    __tablename__ = "children"
    __table_args__ = (
        db.CheckConstraint("age >= 0 AND age <= 18", name="age_range"),
        db.CheckConstraint("age_group IN ('3-6', '7-12')", name="age_group_allowed"),
    )

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(50), nullable=False)
    age = db.Column(db.SmallInteger, nullable=False)
    city = db.Column(db.String(50), nullable=True)
    age_group = db.Column(db.String(16), nullable=False)
    interests = db.Column(db.JSON, nullable=False, default=list)
    is_default = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    user = db.relationship("User", back_populates="children")
    exploration_plans = db.relationship("ExplorationPlan", back_populates="child")
