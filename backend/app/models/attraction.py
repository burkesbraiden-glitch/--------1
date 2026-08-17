from app.extensions import db
from app.utils.time import utc_now


class Attraction(db.Model):
    __tablename__ = "attractions"
    __table_args__ = (
        db.UniqueConstraint("city", "name", name="city_name_unique"),
    )

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    city = db.Column(db.String(80), nullable=False, index=True)
    district = db.Column(db.String(80), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    summary = db.Column(db.Text, nullable=False)
    tags = db.Column(db.JSON, nullable=False, default=list)
    recommended_duration_minutes = db.Column(db.Integer, nullable=True)
    cover_image = db.Column(db.String(500), nullable=True)
    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.text("1"),
        index=True,
    )
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    guide = db.relationship(
        "AttractionGuide",
        back_populates="attraction",
        cascade="all, delete-orphan",
        uselist=False,
    )
