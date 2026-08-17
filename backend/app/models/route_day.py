from app.extensions import db
from app.utils.time import utc_now


class RouteDay(db.Model):
    __tablename__ = "route_days"
    __table_args__ = (
        db.UniqueConstraint("route_id", "day_number", name="route_day_number_unique"),
        db.CheckConstraint("day_number > 0", name="route_day_number_positive"),
    )

    id = db.Column(db.BigInteger, primary_key=True)
    route_id = db.Column(
        db.BigInteger,
        db.ForeignKey("routes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_number = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=True)
    title = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    route = db.relationship("Route", back_populates="days")
    stops = db.relationship(
        "RouteStop",
        back_populates="route_day",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RouteStop.sort_order, RouteStop.id",
    )
