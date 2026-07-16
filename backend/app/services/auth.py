import hashlib

from flask_jwt_extended import create_access_token
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import User
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
    return code


def fixed_code_for_config(config):
    if config["APP_ENV"] not in {"development", "testing"}:
        return None
    return config.get("DEV_FIXED_CODE")


def send_verification_code(payload, config):
    validate_phone_payload(payload)
    if config["APP_ENV"] == "production":
        raise AuthError("SMS_NOT_CONFIGURED", "SMS service not configured", 503)
    if not fixed_code_for_config(config):
        raise AuthError("SMS_NOT_CONFIGURED", "SMS service not configured", 503)
    return {"cooldownSeconds": 60}


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
    if not fixed_code or code != fixed_code:
        raise AuthError("INVALID_VERIFICATION_CODE", "Invalid verification code", 401)

    try:
        user = User.query.filter_by(phone=phone).first()
        if user is None:
            user = User(phone=phone, nickname=DEFAULT_PHONE_NICKNAME)
            db.session.add(user)
            db.session.commit()
        return token_payload_for_user(user, config)
    except SQLAlchemyError:
        db.session.rollback()
        raise AuthError("DATABASE_ERROR", "Database error", 500)


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
