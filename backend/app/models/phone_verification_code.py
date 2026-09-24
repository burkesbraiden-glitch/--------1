from app.extensions import db
from app.utils.time import utc_now


class PhoneVerificationCode(db.Model):
    __tablename__ = "phone_verification_codes"
    __table_args__ = (
        db.CheckConstraint("failed_attempts >= 0", name="failed_attempts_nonnegative"),
    )

    phone = db.Column(db.String(20), primary_key=True)
    code_hash = db.Column(db.String(64), nullable=False)
    sent_at = db.Column(db.DateTime, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    failed_attempts = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    consumed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)
