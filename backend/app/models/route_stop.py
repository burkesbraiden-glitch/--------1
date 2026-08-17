from app.extensions import db
from app.utils.time import utc_now


class RouteStop(db.Model):
    __tablename__ = "route_stops"
    __table_args__ = (
        db.UniqueConstraint("route_day_id", "sort_order", name="route_stop_sort_order_unique"),
        db.CheckConstraint("sort_order > 0", name="route_stop_sort_order_positive"),
    )

    id = db.Column(db.BigInteger, primary_key=True)
    route_day_id = db.Column(
        db.BigInteger,
        db.ForeignKey("route_days.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attraction_id = db.Column(
        db.BigInteger,
        db.ForeignKey("attractions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sort_order = db.Column(db.Integer, nullable=False)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    route_day = db.relationship("RouteDay", back_populates="stops")
    attraction = db.relationship("Attraction")
