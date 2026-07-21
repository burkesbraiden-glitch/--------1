from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import ExplorationPlan, JourneyRecord, Task, TaskSubmission
from app.services.children import get_child_model_for_user
from app.services.plans import PlanError, format_datetime, get_plan_model_for_user
from app.services.tasks import serialize_task
from app.utils.time import utc_now


ALLOWED_STATUSES = {"draft", "finalized"}
CREATE_ALLOWED_PLAN_STATUSES = {"ready", "in-progress", "completed"}
PATCH_ALLOWED_FIELDS = {"customTitle", "summary", "coverSubmissionId"}


class JourneyRecordError(Exception):
    def __init__(self, code, message, status_code):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _query_options():
    return (
        joinedload(JourneyRecord.plan).joinedload(ExplorationPlan.child),
        joinedload(JourneyRecord.plan).selectinload(ExplorationPlan.tasks).joinedload(Task.submission),
        joinedload(JourneyRecord.cover_submission).joinedload(TaskSubmission.task),
    )


def _not_found():
    raise JourneyRecordError("JOURNEY_RECORD_NOT_FOUND", "Journey record not found", 404)


def _database_error():
    raise JourneyRecordError("DATABASE_ERROR", "Database error", 500)


def _invalid_cover_submission():
    raise JourneyRecordError(
        "INVALID_COVER_SUBMISSION",
        "Cover submission is invalid",
        400,
    )


def _find_journey_record_model_for_owned_plan(user, plan_id):
    return (
        JourneyRecord.query.options(*_query_options())
        .join(ExplorationPlan)
        .filter(
            JourneyRecord.plan_id == plan_id,
            ExplorationPlan.user_id == user.id,
        )
        .first()
    )


def get_journey_record_model_for_user(user, record_id):
    record = (
        JourneyRecord.query.options(*_query_options())
        .join(ExplorationPlan)
        .filter(JourneyRecord.id == record_id, ExplorationPlan.user_id == user.id)
        .first()
    )
    if record is None:
        _not_found()
    return record


def get_journey_record_model_for_plan(user, plan_id):
    plan = get_plan_model_for_user(user, plan_id)
    record = _find_journey_record_model_for_owned_plan(user, plan.id)
    if record is None:
        _not_found()
    return record


def _validate_plan_can_create_record(plan):
    if plan.status not in CREATE_ALLOWED_PLAN_STATUSES:
        raise PlanError("PLAN_NOT_READY", "Plan not ready", 409)


def sqlite_next_journey_record_id():
    if db.engine.dialect.name != "sqlite":
        return None
    max_id = db.session.query(db.func.max(JourneyRecord.id)).scalar() or 0
    return max_id + 1


def _is_plan_journey_record_unique_error(error):
    message = str(getattr(error, "orig", error)).lower()
    return "plan_journey_record" in message or "journey_records.plan_id" in message


def create_or_get_journey_record(user, plan_id):
    plan = get_plan_model_for_user(user, plan_id)
    _validate_plan_can_create_record(plan)
    record = _find_journey_record_model_for_owned_plan(user, plan.id)
    if record is not None:
        return record, False

    record = JourneyRecord(id=sqlite_next_journey_record_id(), plan_id=plan.id)
    try:
        db.session.add(record)
        db.session.commit()
        return record, True
    except IntegrityError as error:
        db.session.rollback()
        if not _is_plan_journey_record_unique_error(error):
            _database_error()
        record = _find_journey_record_model_for_owned_plan(user, plan.id)
        if record is not None:
            return record, False
        _database_error()
    except SQLAlchemyError:
        db.session.rollback()
        _database_error()


def _validate_patch_payload(payload):
    if not isinstance(payload, dict):
        raise JourneyRecordError("VALIDATION_ERROR", "Request body must be a JSON object", 400)
    if not payload:
        raise JourneyRecordError("VALIDATION_ERROR", "Request body must not be empty", 400)
    if set(payload) - PATCH_ALLOWED_FIELDS:
        raise JourneyRecordError("VALIDATION_ERROR", "Unknown field", 400)


def _normalize_optional_text(value, field_name, max_length):
    if value is None:
        return None
    if not isinstance(value, str):
        raise JourneyRecordError("VALIDATION_ERROR", f"{field_name} must be a string", 400)
    value = value.strip()
    if not value:
        return None
    if len(value) > max_length:
        raise JourneyRecordError(
            "VALIDATION_ERROR",
            f"{field_name} must be at most {max_length} characters",
            400,
        )
    return value


def _get_cover_submission_for_plan(plan_id, cover_submission_id):
    if isinstance(cover_submission_id, bool) or not isinstance(cover_submission_id, int):
        raise JourneyRecordError("VALIDATION_ERROR", "coverSubmissionId must be an integer", 400)
    if cover_submission_id < 1:
        _invalid_cover_submission()
    submission = (
        TaskSubmission.query.join(Task)
        .filter(
            TaskSubmission.id == cover_submission_id,
            Task.plan_id == plan_id,
        )
        .first()
    )
    if submission is None or not submission.image_url:
        _invalid_cover_submission()
    return submission


def update_journey_record(user, plan_id, payload):
    plan = get_plan_model_for_user(user, plan_id)
    record = _find_journey_record_model_for_owned_plan(user, plan.id)
    if record is None:
        _not_found()
    if record.status == "finalized":
        raise JourneyRecordError(
            "JOURNEY_RECORD_FINALIZED",
            "Journey record is finalized",
            409,
        )
    _validate_patch_payload(payload)

    values = {}
    if "customTitle" in payload:
        values["custom_title"] = _normalize_optional_text(payload["customTitle"], "customTitle", 120)
    if "summary" in payload:
        values["summary"] = _normalize_optional_text(payload["summary"], "summary", 2000)
    if "coverSubmissionId" in payload:
        cover_submission_id = payload["coverSubmissionId"]
        values["cover_submission_id"] = (
            None
            if cover_submission_id is None
            else _get_cover_submission_for_plan(plan.id, cover_submission_id).id
        )

    changes = {
        field: value
        for field, value in values.items()
        if getattr(record, field) != value
    }
    if not changes:
        return record

    try:
        for field, value in changes.items():
            setattr(record, field, value)
        db.session.commit()
        return record
    except SQLAlchemyError:
        db.session.rollback()
        _database_error()


def finalize_journey_record(user, plan_id):
    plan = get_plan_model_for_user(user, plan_id)
    record = _find_journey_record_model_for_owned_plan(user, plan.id)
    if record is None:
        _not_found()
    if record.status == "finalized":
        return record, False
    if record.status != "draft":
        _database_error()

    try:
        record.status = "finalized"
        record.finalized_at = utc_now()
        db.session.commit()
        return record, True
    except SQLAlchemyError:
        db.session.rollback()
        _database_error()


def _validate_pagination(limit, offset):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise JourneyRecordError("VALIDATION_ERROR", "limit must be an integer from 1 to 100", 400)
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise JourneyRecordError("VALIDATION_ERROR", "offset must be a non-negative integer", 400)


def list_journey_record_models_for_user(user, child_id=None, status=None, limit=20, offset=0):
    _validate_pagination(limit, offset)
    if status is not None and status not in ALLOWED_STATUSES:
        raise JourneyRecordError("VALIDATION_ERROR", "status is invalid", 400)
    if child_id is not None:
        get_child_model_for_user(user, child_id)

    query = JourneyRecord.query.join(ExplorationPlan).filter(ExplorationPlan.user_id == user.id)
    if child_id is not None:
        query = query.filter(ExplorationPlan.child_id == child_id)
    if status is not None:
        query = query.filter(JourneyRecord.status == status)
    total = query.count()
    records = (
        query.options(*_query_options())
        .order_by(JourneyRecord.updated_at.desc(), JourneyRecord.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return records, total


def _has_note(submission):
    return bool(submission and isinstance(submission.note, str) and submission.note.strip())


def _serialize_entry(task):
    payload = serialize_task(task)
    submission = task.submission
    return {
        "taskId": task.id,
        "submissionId": submission.id,
        "title": task.title,
        "subtitle": task.subtitle,
        "sortOrder": task.sort_order,
        "status": submission.status,
        "note": payload["record"]["note"],
        "completedAt": payload["completedAt"],
        "imageUrl": payload["record"]["imageUrl"],
    }


def _cover_image_url(record):
    submission = record.cover_submission
    if submission is None or not submission.image_url or submission.task is None:
        return None
    if submission.task.plan_id != record.plan_id:
        return None
    return serialize_task(submission.task)["record"]["imageUrl"]


def serialize_journey_record(record, include_entries=True):
    tasks = sorted(record.plan.tasks or [], key=lambda task: (task.sort_order, task.id))
    submissions = [task.submission for task in tasks if task.submission is not None]
    entries = [
        _serialize_entry(task)
        for task in tasks
        if task.submission is not None
        and (task.submission.status == "completed" or task.submission.image_url or _has_note(task.submission))
    ]
    custom_title = record.custom_title
    payload = {
        "id": record.id,
        "planId": record.plan_id,
        "childId": record.plan.child_id,
        "title": record.plan.title,
        "customTitle": custom_title,
        "displayTitle": custom_title if isinstance(custom_title, str) and custom_title.strip() else record.plan.title,
        "destination": record.plan.destination,
        "planStatus": record.plan.status,
        "status": record.status,
        "summary": record.summary,
        "coverSubmissionId": record.cover_submission_id,
        "coverImageUrl": _cover_image_url(record),
        "taskCount": len(tasks),
        "completedTaskCount": sum(submission.status == "completed" for submission in submissions),
        "photoCount": sum(bool(submission.image_url) for submission in submissions),
        "noteCount": sum(_has_note(submission) for submission in submissions),
        "finalizedAt": format_datetime(record.finalized_at),
        "createdAt": format_datetime(record.created_at),
        "updatedAt": format_datetime(record.updated_at),
    }
    if include_entries:
        payload["entries"] = entries
    return payload
