from app.extensions import db
from app.utils.time import utc_now


class GuideCard(db.Model):
    __tablename__ = "guide_cards"
    __table_args__ = (
        db.CheckConstraint(
            "audio_status IN ('none', 'pending', 'generating', 'ready', 'failed')",
            name="ck_guide_cards_audio_status_allowed",
        ),
    )

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
    narration_text = db.Column(db.Text, nullable=True)
    guide_version = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    audio_status = db.Column(db.String(24), nullable=False, default="none", server_default="none")
    audio_url = db.Column(db.String(500), nullable=True)
    audio_object_key = db.Column(db.String(500), nullable=True)
    audio_source_hash = db.Column(db.String(64), nullable=True)
    audio_generation_token = db.Column(db.String(64), nullable=True)
    audio_duration_sec = db.Column(db.Integer, nullable=True)
    audio_generated_at = db.Column(db.DateTime, nullable=True)
    audio_error_code = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    plan = db.relationship("ExplorationPlan", back_populates="guide_card")
