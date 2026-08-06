from pathlib import Path

from flask import current_app
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.constants import EXPECTED_TASK_COUNT
from app.models import ExplorationPlan, JourneyRecord, Task, TaskSubmission
from app.services.children import get_child_model_for_user
from app.services.journey_record_images import (
    JourneyRecordImageError,
    cleanup_record_image_copies,
    prepare_record_image_copies,
    publish_record_image_copies,
)
from app.services.journey_record_snapshots import (
    JourneyRecordSnapshotValidationError,
    build_journey_record_snapshot_v1,
    validate_journey_record_snapshot,
)
from app.services.plans import PlanError, format_datetime, get_plan_model_for_user
from app.services.tasks import serialize_task
from app.utils.time import utc_now


ALLOWED_STATUSES = {"draft", "finalized"}
CREATE_ALLOWED_PLAN_STATUSES = {"ready", "in-progress", "completed"}
PATCH_ALLOWED_FIELDS = {"customTitle", "summary", "coverSubmissionId"}


class JourneyRecordError(Exception):
    def __init__(self, code, message, status_code, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


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


def _snapshot_invalid():
    raise JourneyRecordError("JOURNEY_RECORD_SNAPSHOT_INVALID", "Journey record snapshot is invalid", 500)


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
    plan, record = get_journey_record_for_finalize(user, plan_id)
    if record.status == "finalized":
        if record.snapshot is not None:
            try:
                validate_journey_record_snapshot(record.snapshot)
            except JourneyRecordSnapshotValidationError:
                _snapshot_invalid()
        return record, False
    if record.status != "draft":
        _database_error()
    if plan.status != "completed":
        raise JourneyRecordError("PLAN_NOT_COMPLETED", "Plan is not completed", 409)

    tasks = (
        Task.query.options(selectinload(Task.submission))
        .filter_by(plan_id=plan.id)
        .order_by(Task.sort_order.asc(), Task.id.asc())
        .all()
    )
    details = _source_completeness_details(tasks)
    if (
        details["taskCount"] != EXPECTED_TASK_COUNT
        or details["missingSubmissionTaskIds"]
        or details["incompleteTaskIds"]
    ):
        raise JourneyRecordError(
            "JOURNEY_RECORD_SOURCE_INCOMPLETE",
            "Journey record source is incomplete",
            409,
            details,
        )
    _validate_finalize_cover(record, tasks)

    prepared = None
    try:
        prepared = prepare_record_image_copies(
            record.id,
            [task.submission for task in tasks],
            task_image_root=Path(current_app.config["TASK_IMAGE_UPLOAD_DIR"]),
            record_image_root=Path(current_app.config["RECORD_IMAGE_UPLOAD_DIR"]),
        )
        finalized_now = utc_now()
        snapshot = build_journey_record_snapshot_v1(
            record,
            plan,
            tasks,
            finalized_at=finalized_now,
            image_assets_by_submission_id=prepared.assets_by_submission_id,
        )
        publish_record_image_copies(prepared)
        record.snapshot = snapshot
        record.status = "finalized"
        record.finalized_at = finalized_now
        record.updated_at = finalized_now
        db.session.commit()
        try:
            cleanup_record_image_copies(prepared)
        except JourneyRecordImageError:
            pass
        return record, True
    except JourneyRecordSnapshotValidationError:
        db.session.rollback()
        _cleanup_finalize_images(prepared)
        _snapshot_invalid()
    except JourneyRecordImageError:
        db.session.rollback()
        _cleanup_finalize_images(prepared)
        raise
    except SQLAlchemyError:
        db.session.rollback()
        _cleanup_finalize_images(prepared)
        _database_error()


def get_journey_record_for_finalize(user, plan_id):
    plan = (
        ExplorationPlan.query.filter_by(id=plan_id, user_id=user.id)
        .with_for_update()
        .first()
    )
    if plan is None:
        raise PlanError("PLAN_NOT_FOUND", "Plan not found", 404)
    record = JourneyRecord.query.filter_by(plan_id=plan.id).with_for_update().first()
    if record is None:
        _not_found()
    return plan, record


def _source_completeness_details(tasks):
    return {
        "expectedTaskCount": EXPECTED_TASK_COUNT,
        "taskCount": len(tasks),
        "completedTaskCount": sum(
            task.submission is not None and task.submission.status == "completed"
            for task in tasks
        ),
        "missingSubmissionTaskIds": [task.id for task in tasks if task.submission is None],
        "incompleteTaskIds": [
            task.id
            for task in tasks
            if task.submission is not None and task.submission.status != "completed"
        ],
    }


def _validate_finalize_cover(record, tasks):
    if record.cover_submission_id is None:
        return
    cover = next((task.submission for task in tasks if task.submission.id == record.cover_submission_id), None)
    if cover is None or not _is_safe_task_image_key(cover.image_url):
        _invalid_cover_submission()


def _is_safe_task_image_key(value):
    if not isinstance(value, str) or not value.startswith("task-images/") or "\\" in value:
        return False
    filename = value.removeprefix("task-images/")
    return bool(filename) and "/" not in filename and filename not in {".", ".."}


def _cleanup_finalize_images(prepared):
    if prepared is None:
        return
    cleanup_record_image_copies(prepared, remove_published=True)


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
    if record.status == "finalized" and record.snapshot is not None:
        return _serialize_snapshot_journey_record(record, include_entries=include_entries)
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


def _record_image_url(record_id, asset_id):
    return None if asset_id is None else f"/api/v1/journey-records/{record_id}/images/{asset_id}"


def _serialize_snapshot_journey_record(record, *, include_entries):
    try:
        snapshot = validate_journey_record_snapshot(record.snapshot)
    except JourneyRecordSnapshotValidationError:
        _snapshot_invalid()
    values = snapshot["record"]
    payload = {
        "id": values["id"],
        "planId": values["planId"],
        "childId": values["childId"],
        "title": values["title"],
        "customTitle": values["customTitle"],
        "displayTitle": values["displayTitle"],
        "destination": values["destination"],
        "planStatus": values["planStatus"],
        "status": values["status"],
        "summary": values["summary"],
        "coverSubmissionId": values["coverSubmissionId"],
        "coverImageUrl": _record_image_url(record.id, snapshot["cover"]["imageAssetId"]),
        "taskCount": values["taskCount"],
        "completedTaskCount": values["completedTaskCount"],
        "photoCount": values["photoCount"],
        "noteCount": values["noteCount"],
        "finalizedAt": values["finalizedAt"],
        "createdAt": values["createdAt"],
        "updatedAt": values["updatedAt"],
    }
    if include_entries:
        payload["entries"] = [
            {
                "taskId": entry["taskId"],
                "submissionId": entry["submissionId"],
                "title": entry["title"],
                "subtitle": entry["subtitle"],
                "sortOrder": entry["sortOrder"],
                "status": entry["status"],
                "note": entry["note"],
                "completedAt": entry["completedAt"],
                "imageUrl": _record_image_url(record.id, entry["imageAssetId"]),
            }
            for entry in snapshot["entries"]
        ]
    return payload
