from app.extensions import db
from app.utils.time import utc_now


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        db.CheckConstraint(
            "phone IS NOT NULL OR wechat_openid IS NOT NULL",
            name="has_login_identifier",
        ),
    )

    id = db.Column(db.BigInteger, primary_key=True)
    phone = db.Column(db.String(20), nullable=True, unique=True, index=True)
    nickname = db.Column(db.String(50), nullable=False)
    city = db.Column(db.String(50), nullable=True)
    wechat_openid = db.Column(db.String(128), nullable=True, unique=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    children = db.relationship(
        "Child",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    exploration_plans = db.relationship(
        "ExplorationPlan",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
