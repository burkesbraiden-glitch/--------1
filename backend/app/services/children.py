import re

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.constants import CHILD_AVATAR_PRESET_KEYS, CHILD_PRIVACY_CONSENT_VERSION
from app.extensions import db
from app.models import Child, ExplorationPlan, GuideAudioJob, GuideCard, JourneyRecord, Task, TaskSubmission
from app.services.audio_storage import create_audio_storage
from app.utils.time import utc_now


ALLOWED_CREATE_FIELDS = {"name", "age", "city", "avatarPreset", "interests", "guardianConsent"}
ALLOWED_PATCH_FIELDS = {"name", "age", "city", "avatarPreset", "interests", "guardianConsent"}
_GUIDE_AUDIO_OBJECT_KEY_PATTERN = re.compile(
    r"^guide-audio/(?P<guide_id>[1-9][0-9]*)/[0-9a-f]{64}/[0-9a-f]{32}\.mp3$"
)


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
    raise ChildError("INVALID_CHILD_AGE", "age must be between 3 and 12", 400)


def normalize_name(payload):
    name = payload.get("name")
    if not isinstance(name, str):
        raise ChildError("INVALID_CHILD_NAME", "name is required", 400)
    name = name.strip()
    if not 1 <= len(name) <= 50:
        raise ChildError("INVALID_CHILD_NAME", "name must be 1 to 50 characters", 400)
    return name


def normalize_age(payload, current_age=None):
    if "age" not in payload:
        if current_age is None:
            raise ChildError("INVALID_CHILD_AGE", "age is required", 400)
        return current_age
    age = payload["age"]
    if isinstance(age, bool) or not isinstance(age, int):
        raise ChildError("INVALID_CHILD_AGE", "age must be an integer", 400)
    if not 3 <= age <= 12:
        raise ChildError("INVALID_CHILD_AGE", "age must be between 3 and 12", 400)
    return age


def normalize_city(payload):
    if "city" not in payload or payload["city"] is None:
        return None
    city = payload["city"]
    if not isinstance(city, str):
        raise ChildError("INVALID_CHILD_CITY", "city must be a string", 400)
    city = city.strip()
    if not city:
        return None
    if len(city) > 50:
        raise ChildError("INVALID_CHILD_CITY", "city must be at most 50 characters", 400)
    return city


def normalize_interests(payload, current_interests=None):
    if "interests" not in payload:
        return [] if current_interests is None else current_interests
    interests = payload["interests"]
    if not isinstance(interests, list):
        raise ChildError("INVALID_CHILD_INTERESTS", "interests must be an array", 400)
    if len(interests) > 10:
        raise ChildError("INVALID_CHILD_INTERESTS", "interests can contain at most 10 items", 400)
    normalized = []
    seen = set()
    for interest in interests:
        if not isinstance(interest, str):
            raise ChildError("INVALID_CHILD_INTERESTS", "interests must be strings", 400)
        value = interest.strip()
        if not value or len(value) > 30:
            raise ChildError("INVALID_CHILD_INTERESTS", "interest must be 1 to 30 characters", 400)
        if value not in seen:
            seen.add(value)
            normalized.append(value)
    return normalized


def normalize_avatar_preset(payload, current_avatar_preset=None, *, required=False):
    if "avatarPreset" not in payload:
        if required:
            raise ChildError("INVALID_CHILD_AVATAR", "Avatar preset is required", 400)
        return current_avatar_preset
    avatar_preset = payload["avatarPreset"]
    if not isinstance(avatar_preset, str) or avatar_preset not in CHILD_AVATAR_PRESET_KEYS:
        raise ChildError("INVALID_CHILD_AVATAR", "Avatar preset is not available", 400)
    return avatar_preset


def require_guardian_consent(payload):
    if payload.get("guardianConsent") is not True:
        raise ChildError("GUARDIAN_CONSENT_REQUIRED", "Guardian consent is required", 400)


def apply_patch_guardian_consent(child, payload):
    if "guardianConsent" not in payload:
        return
    if payload["guardianConsent"] is not True:
        raise ChildError(
            "GUARDIAN_CONSENT_CANNOT_BE_REVOKED",
            "Guardian consent cannot be revoked through child editing",
            400,
        )
    if child.guardian_consent_at is None:
        child.guardian_consent_at = utc_now()
        child.guardian_consent_version = CHILD_PRIVACY_CONSENT_VERSION
        child.guardian_consent_source = "child_edit"


def serialize_child(child):
    return {
        "id": child.id,
        "name": child.name,
        "age": child.age,
        "city": child.city,
        "avatarPreset": child.avatar_preset,
        "ageGroup": child.age_group,
        "interests": child.interests or [],
        "isDefault": child.is_default,
        "guardianConsentGranted": child.guardian_consent_at is not None,
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


def choose_default_child(children, *, deleted_default=False):
    if not children:
        return None
    if deleted_default:
        return children[0]
    default_children = [child for child in children if child.is_default]
    return default_children[0] if len(default_children) == 1 else (default_children or children)[0]


def set_exactly_one_default(user, *, deleted_default=False):
    children = children_query(user).order_by(Child.created_at.asc(), Child.id.asc()).all()
    selected = choose_default_child(children, deleted_default=deleted_default)
    if selected is None:
        return None
    for child in children:
        child.is_default = child.id == selected.id
    return selected


def next_sqlite_child_id():
    if db.engine.dialect.name != "sqlite":
        return None
    return (db.session.query(db.func.max(Child.id)).scalar() or 0) + 1


def create_child(user, payload):
    validate_create_payload(payload)
    require_guardian_consent(payload)
    name = normalize_name(payload)
    age = normalize_age(payload)
    city = normalize_city(payload)
    avatar_preset = normalize_avatar_preset(payload, required=True)
    interests = normalize_interests(payload)
    existing_count = children_query(user).count()

    try:
        child_values = {
            "user_id": user.id,
            "name": name,
            "age": age,
            "city": city,
            "avatar_preset": avatar_preset,
            "age_group": age_group_for_age(age),
            "interests": interests,
            "is_default": existing_count == 0,
            "guardian_consent_at": utc_now(),
            "guardian_consent_version": CHILD_PRIVACY_CONSENT_VERSION,
            "guardian_consent_source": "child_create",
        }
        sqlite_child_id = next_sqlite_child_id()
        if sqlite_child_id is not None:
            child_values["id"] = sqlite_child_id
        child = Child(**child_values)
        db.session.add(child)
        db.session.flush()
        set_exactly_one_default(user)
        db.session.commit()
        return serialize_child(child)
    except SQLAlchemyError:
        db.session.rollback()
        raise ChildError("DATABASE_ERROR", "Database error", 500)


def validate_create_payload(payload):
    unknown = set(payload) - ALLOWED_CREATE_FIELDS
    if unknown:
        raise ChildError("VALIDATION_ERROR", "Unknown field", 400)


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
    city = normalize_city(payload) if "city" in payload else child.city
    avatar_preset = normalize_avatar_preset(payload, child.avatar_preset)
    interests = normalize_interests(payload, child.interests or []) if "interests" in payload else child.interests

    apply_patch_guardian_consent(child, payload)

    try:
        child.name = name
        child.age = age
        child.age_group = age_group_for_age(age)
        child.city = city
        child.avatar_preset = avatar_preset
        child.interests = interests
        db.session.commit()
        return serialize_child(child)
    except SQLAlchemyError:
        db.session.rollback()
        raise ChildError("DATABASE_ERROR", "Database error", 500)


def _guide_audio_key_is_controlled(guide, object_key):
    if not isinstance(object_key, str):
        return False
    match = _GUIDE_AUDIO_OBJECT_KEY_PATTERN.fullmatch(object_key)
    return match is not None and int(match.group("guide_id")) == guide.id


def _unreferenced_task_image(storage_key):
    return TaskSubmission.query.filter_by(image_url=storage_key).first() is None


def _cleanup_task_image(storage_key):
    if not _unreferenced_task_image(storage_key):
        return
    from app.services.task_images import TaskError, cleanup_file, path_for_storage_key

    try:
        cleanup_file(path_for_storage_key(storage_key))
    except TaskError:
        current_app.logger.warning("child_deletion_task_image_cleanup_skipped")
    except Exception:
        current_app.logger.warning("child_deletion_task_image_cleanup_failed")


def _cleanup_record_images(record_id):
    if db.session.get(JourneyRecord, record_id) is not None:
        return
    from app.services.journey_record_images import JourneyRecordImageError, delete_record_image_assets

    try:
        delete_record_image_assets(
            record_id,
            record_image_root=current_app.config["RECORD_IMAGE_UPLOAD_DIR"],
        )
    except JourneyRecordImageError:
        current_app.logger.warning("child_deletion_record_image_cleanup_failed")
    except Exception:
        current_app.logger.warning("child_deletion_record_image_cleanup_failed")


def _cleanup_guide_audio(storage, object_key):
    if GuideCard.query.filter_by(audio_object_key=object_key).first() is not None:
        return
    try:
        storage.delete(object_key=object_key)
    except Exception:
        current_app.logger.warning("child_deletion_guide_audio_cleanup_failed")


def cleanup_deleted_child_assets(*, task_image_keys, record_ids, guide_audio_keys, audio_storage=None):
    for storage_key in task_image_keys:
        _cleanup_task_image(storage_key)
    for record_id in record_ids:
        _cleanup_record_images(record_id)
    if not guide_audio_keys:
        return
    storage = audio_storage
    if storage is None:
        try:
            storage = create_audio_storage(current_app.config)
        except Exception:
            current_app.logger.warning("child_deletion_guide_audio_storage_unavailable")
            return
    for object_key in guide_audio_keys:
        _cleanup_guide_audio(storage, object_key)


def delete_child(user, child_id, *, audio_storage=None):
    child = get_child_model_for_user(user, child_id)
    deleted_default = child.is_default
    plans = ExplorationPlan.query.filter_by(child_id=child.id).order_by(ExplorationPlan.id.asc()).all()
    plan_ids = [plan.id for plan in plans]
    tasks = Task.query.filter(Task.plan_id.in_(plan_ids)).order_by(Task.id.asc()).all() if plan_ids else []
    task_ids = [task.id for task in tasks]
    submissions = (
        TaskSubmission.query.filter(TaskSubmission.task_id.in_(task_ids)).order_by(TaskSubmission.id.asc()).all()
        if task_ids
        else []
    )
    records = (
        JourneyRecord.query.filter(JourneyRecord.plan_id.in_(plan_ids)).order_by(JourneyRecord.id.asc()).all()
        if plan_ids
        else []
    )
    guides = (
        GuideCard.query.filter(GuideCard.plan_id.in_(plan_ids)).order_by(GuideCard.id.asc()).all()
        if plan_ids
        else []
    )
    guide_ids = [guide.id for guide in guides]
    jobs = (
        GuideAudioJob.query.filter(GuideAudioJob.guide_id.in_(guide_ids)).order_by(GuideAudioJob.id.asc()).all()
        if guide_ids
        else []
    )

    task_image_keys = tuple(sorted({submission.image_url for submission in submissions if submission.image_url}))
    record_ids = tuple(record.id for record in records)
    guide_audio_keys = tuple(
        sorted(
            {
                guide.audio_object_key
                for guide in guides
                if _guide_audio_key_is_controlled(guide, guide.audio_object_key)
            }
        )
    )

    try:
        for record in records:
            db.session.delete(record)
        db.session.flush()
        for submission in submissions:
            db.session.delete(submission)
        db.session.flush()
        for job in jobs:
            db.session.delete(job)
        db.session.flush()
        for guide in guides:
            db.session.delete(guide)
        db.session.flush()
        for task in tasks:
            db.session.delete(task)
        db.session.flush()
        for plan in plans:
            db.session.delete(plan)
        db.session.flush()
        db.session.delete(child)
        db.session.flush()
        set_exactly_one_default(user, deleted_default=deleted_default)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise ChildError("DATABASE_ERROR", "Database error", 500)

    cleanup_deleted_child_assets(
        task_image_keys=task_image_keys,
        record_ids=record_ids,
        guide_audio_keys=guide_audio_keys,
        audio_storage=audio_storage,
    )
    result = list_children(user)
    return {"deletedChildId": child_id, **result}
