from app.extensions import db
from app.utils.time import utc_now


class Route(db.Model):
    __tablename__ = "routes"
    __table_args__ = (
        db.CheckConstraint("status IN ('draft', 'ready')", name="route_status_allowed"),
    )

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(80), nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(24), nullable=False, default="draft", server_default="draft")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    user = db.relationship("User", back_populates="routes")
    days = db.relationship(
        "RouteDay",
        back_populates="route",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RouteDay.day_number, RouteDay.id",
    )
