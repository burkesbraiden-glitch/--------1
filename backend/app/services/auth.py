import hashlib
import hmac
import secrets
from datetime import timedelta

from flask_jwt_extended import create_access_token
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import PhoneVerificationCode, User
from app.services.sms import SMSProviderError, get_sms_provider
from app.utils.time import utc_now
from app.utils.validation import is_valid_phone, normalize_phone


DEFAULT_PHONE_NICKNAME = "童旅用户"
DEFAULT_WECHAT_NICKNAME = "微信探索者"
DEFAULT_MOCK_CODE = "local-dev"


class AuthError(Exception):
    def __init__(self, code, message, status_code):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def validate_phone_payload(payload):
    phone = payload.get("phone")
    if phone is None:
        raise AuthError("VALIDATION_ERROR", "phone is required", 400)
    if not isinstance(phone, str):
        raise AuthError("VALIDATION_ERROR", "phone must be a string", 400)
    phone = normalize_phone(phone)
    if not is_valid_phone(phone):
        raise AuthError("INVALID_PHONE", "Invalid phone number", 400)
    return phone


def validate_code_payload(payload):
    code = payload.get("code")
    if code is None:
        raise AuthError("VALIDATION_ERROR", "code is required", 400)
    if not isinstance(code, str):
        raise AuthError("VALIDATION_ERROR", "code must be a string", 400)
    code = code.strip()
    if len(code) != 6 or not code.isdigit():
        raise AuthError("INVALID_VERIFICATION_CODE", "Invalid verification code", 401)
    return code


def fixed_code_for_config(config):
    if config["APP_ENV"] not in {"development", "testing"}:
        return None
    return config.get("DEV_FIXED_CODE")


def generate_verification_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def verification_code_hash(phone, code, config):
    secret = config["SMS_VERIFICATION_SECRET"].encode("utf-8")
    message = f"{phone}:{code}".encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def _commit_or_raise_database_error():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise AuthError("DATABASE_ERROR", "Database error", 500)


def _login_phone_user(phone, config, verification_record=None):
    try:
        user = User.query.filter_by(phone=phone).first()
        if user is None:
            user = User(phone=phone, nickname=DEFAULT_PHONE_NICKNAME)
            db.session.add(user)
        if verification_record is not None:
            verification_record.consumed_at = utc_now()
        db.session.commit()
        return token_payload_for_user(user, config)
    except SQLAlchemyError:
        db.session.rollback()
        raise AuthError("DATABASE_ERROR", "Database error", 500)


def _verify_production_code(phone, code, config):
    record = db.session.get(PhoneVerificationCode, phone)
    now = utc_now()
    if record is None or record.consumed_at is not None:
        raise AuthError("INVALID_VERIFICATION_CODE", "Invalid verification code", 401)

    if record.expires_at <= now:
        record.consumed_at = now
        _commit_or_raise_database_error()
        raise AuthError("VERIFICATION_CODE_EXPIRED", "Verification code expired", 401)

    max_attempts = config["SMS_MAX_VERIFY_ATTEMPTS"]
    if record.failed_attempts >= max_attempts:
        record.consumed_at = now
        _commit_or_raise_database_error()
        raise AuthError("VERIFICATION_CODE_ATTEMPTS_EXCEEDED", "Verification attempts exceeded", 429)

    expected_hash = verification_code_hash(phone, code, config)
    if not hmac.compare_digest(record.code_hash, expected_hash):
        record.failed_attempts += 1
        if record.failed_attempts >= max_attempts:
            record.consumed_at = now
            _commit_or_raise_database_error()
            raise AuthError("VERIFICATION_CODE_ATTEMPTS_EXCEEDED", "Verification attempts exceeded", 429)
        _commit_or_raise_database_error()
        raise AuthError("INVALID_VERIFICATION_CODE", "Invalid verification code", 401)

    return record


def send_verification_code(payload, config):
    phone = validate_phone_payload(payload)
    if config["APP_ENV"] != "production":
        if not fixed_code_for_config(config):
            raise AuthError("SMS_NOT_CONFIGURED", "SMS service not configured", 503)
        return {"cooldownSeconds": 60}

    now = utc_now()
    record = db.session.get(PhoneVerificationCode, phone)
    cooldown_seconds = config["SMS_SEND_COOLDOWN_SECONDS"]
    if record is not None and now < record.sent_at + timedelta(seconds=cooldown_seconds):
        raise AuthError("SMS_COOLDOWN", "Please wait before requesting another code", 429)

    code = generate_verification_code()
    try:
        get_sms_provider(config).send_verification_code(phone, code)
    except SMSProviderError:
        raise AuthError("SMS_PROVIDER_UNAVAILABLE", "SMS provider is temporarily unavailable", 503)

    expires_at = now + timedelta(seconds=config["SMS_CODE_TTL_SECONDS"])
    if record is None:
        record = PhoneVerificationCode(phone=phone)
        db.session.add(record)
    record.code_hash = verification_code_hash(phone, code, config)
    record.sent_at = now
    record.expires_at = expires_at
    record.failed_attempts = 0
    record.consumed_at = None
    _commit_or_raise_database_error()

    return {"cooldownSeconds": cooldown_seconds}


def serialize_user(user):
    return {
        "id": user.id,
        "phone": user.phone,
        "nickname": user.nickname,
        "city": user.city,
    }


def token_payload_for_user(user, config):
    return {
        "accessToken": create_access_token(identity=str(user.id)),
        "tokenType": "Bearer",
        "expiresInHours": config["JWT_ACCESS_TOKEN_HOURS"],
        "user": serialize_user(user),
    }


def login_with_phone(payload, config):
    phone = validate_phone_payload(payload)
    code = validate_code_payload(payload)
    fixed_code = fixed_code_for_config(config)
    if fixed_code:
        if code != fixed_code:
            raise AuthError("INVALID_VERIFICATION_CODE", "Invalid verification code", 401)
        return _login_phone_user(phone, config)

    verification_record = _verify_production_code(phone, code, config)
    return _login_phone_user(phone, config, verification_record)


def mock_openid_from_code(mock_code):
    digest = hashlib.sha256(mock_code.encode("utf-8")).hexdigest()[:24]
    return f"mock:{digest}"


def login_with_mock_wechat(payload, config):
    if config["APP_ENV"] == "production":
        raise AuthError("FEATURE_DISABLED", "Feature disabled", 403)
    mock_code = payload.get("mockCode", DEFAULT_MOCK_CODE)
    if not isinstance(mock_code, str):
        raise AuthError("VALIDATION_ERROR", "mockCode must be a string", 400)
    openid = mock_openid_from_code(mock_code or DEFAULT_MOCK_CODE)

    try:
        user = User.query.filter_by(wechat_openid=openid).first()
        if user is None:
            user = User(wechat_openid=openid, nickname=DEFAULT_WECHAT_NICKNAME)
            db.session.add(user)
            db.session.commit()
        return token_payload_for_user(user, config)
    except SQLAlchemyError:
        db.session.rollback()
        raise AuthError("DATABASE_ERROR", "Database error", 500)


def get_user_by_identity(identity):
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        raise AuthError("UNAUTHORIZED", "Unauthorized", 401)
    user = db.session.get(User, user_id)
    if user is None:
        raise AuthError("UNAUTHORIZED", "Unauthorized", 401)
    return user
