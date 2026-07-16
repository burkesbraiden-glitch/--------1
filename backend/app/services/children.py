from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Child


ALLOWED_PATCH_FIELDS = {"name", "age", "city", "ageGroup", "interests", "isDefault"}


class ChildError(Exception):
    def __init__(self, code, message, status_code):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def age_group_for_age(age):
    if 3 <= age <= 6:
        return "3-6"
    if 7 <= age <= 12:
        return "7-12"
    raise ChildError("VALIDATION_ERROR", "age must be between 3 and 12", 400)


def normalize_name(payload):
    name = payload.get("name")
    if not isinstance(name, str):
        raise ChildError("VALIDATION_ERROR", "name is required", 400)
    name = name.strip()
    if not 1 <= len(name) <= 50:
        raise ChildError("VALIDATION_ERROR", "name must be 1 to 50 characters", 400)
    return name


def normalize_age(payload, current_age=None):
    if "age" not in payload:
        if current_age is None:
            raise ChildError("VALIDATION_ERROR", "age is required", 400)
        return current_age
    age = payload["age"]
    if isinstance(age, bool) or not isinstance(age, int):
        raise ChildError("VALIDATION_ERROR", "age must be an integer", 400)
    if not 3 <= age <= 12:
        raise ChildError("VALIDATION_ERROR", "age must be between 3 and 12", 400)
    return age


def normalize_city(payload):
    if "city" not in payload or payload["city"] is None:
        return None
    city = payload["city"]
    if not isinstance(city, str):
        raise ChildError("VALIDATION_ERROR", "city must be a string", 400)
    city = city.strip()
    if not city:
        return None
    if len(city) > 50:
        raise ChildError("VALIDATION_ERROR", "city must be at most 50 characters", 400)
    return city


def normalize_interests(payload, current_interests=None):
    if "interests" not in payload:
        return [] if current_interests is None else current_interests
    interests = payload["interests"]
    if not isinstance(interests, list):
        raise ChildError("VALIDATION_ERROR", "interests must be an array", 400)
    if len(interests) > 10:
        raise ChildError("VALIDATION_ERROR", "interests can contain at most 10 items", 400)
    normalized = []
    seen = set()
    for interest in interests:
        if not isinstance(interest, str):
            raise ChildError("VALIDATION_ERROR", "interests must be strings", 400)
        value = interest.strip()
        if not value or len(value) > 30:
            raise ChildError("VALIDATION_ERROR", "interest must be 1 to 30 characters", 400)
        if value not in seen:
            seen.add(value)
            normalized.append(value)
    return normalized


def normalize_age_group(payload, age):
    inferred = age_group_for_age(age)
    if "ageGroup" not in payload:
        return inferred
    age_group = payload["ageGroup"]
    if not isinstance(age_group, str):
        raise ChildError("VALIDATION_ERROR", "ageGroup must be a string", 400)
    if age_group != inferred:
        raise ChildError("VALIDATION_ERROR", "ageGroup does not match age", 400)
    return age_group


def normalize_is_default(payload, default=False):
    if "isDefault" not in payload:
        return default
    value = payload["isDefault"]
    if not isinstance(value, bool):
        raise ChildError("VALIDATION_ERROR", "isDefault must be a boolean", 400)
    return value


def serialize_child(child):
    return {
        "id": child.id,
        "name": child.name,
        "age": child.age,
        "city": child.city,
        "ageGroup": child.age_group,
        "interests": child.interests or [],
        "isDefault": child.is_default,
    }


def children_query(user):
    return Child.query.filter_by(user_id=user.id)


def ordered_children(user):
    return children_query(user).order_by(Child.is_default.desc(), Child.created_at.asc()).all()


def list_children(user):
    children = ordered_children(user)
    current = next((child for child in children if child.is_default), None)
    if current is None and children:
        current = children[0]
    return {
        "children": [serialize_child(child) for child in children],
        "currentChild": serialize_child(current) if current else None,
    }


def get_child_model_for_user(user, child_id):
    child = Child.query.filter_by(id=child_id, user_id=user.id).first()
    if child is None:
        raise ChildError("CHILD_NOT_FOUND", "Child not found", 404)
    return child


def get_child_for_user(user, child_id):
    return serialize_child(get_child_model_for_user(user, child_id))


def clear_other_defaults(user, except_child_id=None):
    query = children_query(user)
    if except_child_id is not None:
        query = query.filter(Child.id != except_child_id)
    query.update({"is_default": False}, synchronize_session=False)


def create_child(user, payload):
    name = normalize_name(payload)
    age = normalize_age(payload)
    age_group = normalize_age_group(payload, age)
    city = normalize_city(payload)
    interests = normalize_interests(payload)
    existing_count = children_query(user).count()
    is_default = True if existing_count == 0 else normalize_is_default(payload, False)

    try:
        if is_default:
            clear_other_defaults(user)
        child = Child(
            user_id=user.id,
            name=name,
            age=age,
            city=city,
            age_group=age_group,
            interests=interests,
            is_default=is_default,
        )
        db.session.add(child)
        db.session.commit()
        return serialize_child(child)
    except SQLAlchemyError:
        db.session.rollback()
        raise ChildError("DATABASE_ERROR", "Database error", 500)


def validate_patch_payload(payload):
    if not payload:
        raise ChildError("VALIDATION_ERROR", "Request body must not be empty", 400)
    unknown = set(payload) - ALLOWED_PATCH_FIELDS
    if unknown:
        raise ChildError("VALIDATION_ERROR", "Unknown field", 400)


def update_child(user, child_id, payload):
    validate_patch_payload(payload)
    child = get_child_model_for_user(user, child_id)

    name = normalize_name(payload) if "name" in payload else child.name
    age = normalize_age(payload, child.age)
    age_group = normalize_age_group(payload, age) if ("age" in payload or "ageGroup" in payload) else child.age_group
    city = normalize_city(payload) if "city" in payload else child.city
    interests = normalize_interests(payload, child.interests or []) if "interests" in payload else child.interests
    requested_default = normalize_is_default(payload, child.is_default) if "isDefault" in payload else child.is_default

    if "isDefault" in payload and child.is_default and requested_default is False:
        raise ChildError("DEFAULT_CHILD_REQUIRED", "Default child required", 409)

    try:
        if requested_default is True:
            clear_other_defaults(user, except_child_id=child.id)
        child.name = name
        child.age = age
        child.age_group = age_group
        child.city = city
        child.interests = interests
        child.is_default = requested_default
        db.session.commit()
        return serialize_child(child)
    except SQLAlchemyError:
        db.session.rollback()
        raise ChildError("DATABASE_ERROR", "Database error", 500)
