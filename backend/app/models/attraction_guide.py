from app.extensions import db
from app.utils.time import utc_now


class AttractionGuide(db.Model):
    __tablename__ = "attraction_guides"

    id = db.Column(db.BigInteger, primary_key=True)
    attraction_id = db.Column(
        db.BigInteger,
        db.ForeignKey("attractions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    overview = db.Column(db.Text, nullable=False)
    highlights = db.Column(db.JSON, nullable=False, default=list)
    visit_tips = db.Column(db.JSON, nullable=False, default=list)
    family_tips = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    attraction = db.relationship("Attraction", back_populates="guide")
