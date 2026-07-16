from app.extensions import db
from app.utils.time import utc_now


class GuideCard(db.Model):
    __tablename__ = "guide_cards"

    id = db.Column(db.BigInteger, primary_key=True)
    plan_id = db.Column(
        db.BigInteger,
        db.ForeignKey("exploration_plans.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    child_intro = db.Column(db.JSON, nullable=False, default=list)
    questions = db.Column(db.JSON, nullable=False, default=list)
    focus_items = db.Column(db.JSON, nullable=False, default=list)
    audio_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    plan = db.relationship("ExplorationPlan", back_populates="guide_card")
