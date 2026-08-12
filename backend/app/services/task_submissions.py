from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import ExplorationPlan, JourneyRecord, Task, TaskSubmission
from app.services.plans import PlanError, get_plan_model_for_user
from app.services.tasks import TaskError, serialize_task
from app.utils.time import utc_now


PATCH_ALLOWED_FIELDS = {"note"}
COMPLETE_ALLOWED_FIELDS = {"note"}
PLAN_STATUS_ERRORS = {
    "draft": ("PLAN_NOT_READY", "Plan not ready"),
    "ready": ("PLAN_NOT_STARTED", "Plan not started"),
    "completed": ("PLAN_ALREADY_COMPLETED", "Plan already completed"),
}


def validate_plan_can_change_submissions(plan):
    if plan.status == "in-progress":
        return
    code, message = PLAN_STATUS_ERRORS.get(plan.status, ("PLAN_NOT_READY", "Plan not ready"))
    raise TaskError(code, message, 409)


def get_task_model_for_submission(user, plan_id, task_id, *, validate_plan_status=True):
    plan = get_plan_model_for_user(user, plan_id)
    if validate_plan_status:
        validate_plan_can_change_submissions(plan)
    task = (
        Task.query.options(joinedload(Task.submission))
        .filter_by(id=task_id, plan_id=plan.id)
        .first()
    )
    if task is None:
        raise TaskError("TASK_NOT_FOUND", "Task not found", 404)
    return task


def get_task_model_for_completed_plan_correction(user, plan_id, task_id):
    plan = (
        ExplorationPlan.query.filter_by(id=plan_id, user_id=user.id)
        .with_for_update()
        .first()
    )
    if plan is None:
        raise PlanError("PLAN_NOT_FOUND", "Plan not found", 404)
    if plan.status != "completed":
        validate_plan_can_change_submissions(plan)

    record = JourneyRecord.query.filter_by(plan_id=plan.id).with_for_update().first()
    if record is not None and record.status == "finalized":
        raise TaskError("JOURNEY_RECORD_FINALIZED", "Journey record is finalized", 409)

    task = (
        Task.query.options(joinedload(Task.submission))
        .filter_by(id=task_id, plan_id=plan.id)
        .first()
    )
    if task is None:
        raise TaskError("TASK_NOT_FOUND", "Task not found", 404)
    if task.submission is None or task.submission.status != "completed":
        raise TaskError(
            "TASK_CORRECTION_REQUIRES_COMPLETED_SUBMISSION",
            "Task correction requires a completed submission",
            409,
        )
    return task


def next_sqlite_submission_id():
    if db.engine.dialect.name != "sqlite":
        return None
    max_id = db.session.query(db.func.max(TaskSubmission.id)).scalar() or 0
    return max_id + 1


def build_submission(task_id, status, note=None, completed_at=None):
    return TaskSubmission(
        id=next_sqlite_submission_id(),
        task_id=task_id,
        status=status,
        image_url=None,
        note=note,
        completed_at=completed_at,
    )


def get_existing_submission(task_id):
    return TaskSubmission.query.filter_by(task_id=task_id).first()


def attach_existing_submission(task):
    db.session.refresh(task)
    task.submission = get_existing_submission(task.id)
    return task.submission


def create_submission_with_retry(task, status, note=None, completed_at=None):
    submission = build_submission(task.id, status, note=note, completed_at=completed_at)
    db.session.add(submission)
    try:
        db.session.flush()
        task.submission = submission
        return submission, True
    except IntegrityError:
        db.session.rollback()
        existing = attach_existing_submission(task)
        if existing is None:
            raise TaskError("DATABASE_ERROR", "Database error", 500)
        return existing, False


def ensure_submission(task, status, note=None, completed_at=None):
    if task.submission is not None:
        return task.submission, False
    return create_submission_with_retry(task, status, note=note, completed_at=completed_at)


def validate_payload_object(payload):
    return payload if isinstance(payload, dict) else {}


def validate_allowed_fields(payload, allowed_fields):
    if not payload:
        raise TaskError("VALIDATION_ERROR", "Request body must not be empty", 400)
    if set(payload) - allowed_fields:
        raise TaskError("VALIDATION_ERROR", "Unknown field", 400)


def normalize_note(payload, *, required):
    if "note" not in payload:
        if required:
            raise TaskError("VALIDATION_ERROR", "note is required", 400)
        return None
    note = payload["note"]
    if not isinstance(note, str):
        raise TaskError("VALIDATION_ERROR", "note must be a string", 400)
    note = note.strip()
    if len(note) > 2000:
        raise TaskError("VALIDATION_ERROR", "note must be at most 2000 characters", 400)
    return note


def start_task_submission(user, plan_id, task_id):
    task = get_task_model_for_submission(user, plan_id, task_id)
    try:
        if task.submission is not None:
            if task.submission.status == "completed":
                raise TaskError("TASK_ALREADY_COMPLETED", "Task already completed", 409)
            return serialize_task(task), False

        submission, created = ensure_submission(task, "in-progress", note=None, completed_at=None)
        if submission.status == "completed":
            raise TaskError("TASK_ALREADY_COMPLETED", "Task already completed", 409)
        db.session.commit()
        return serialize_task(task), created
    except TaskError:
        db.session.rollback()
        raise
    except SQLAlchemyError:
        db.session.rollback()
        raise TaskError("DATABASE_ERROR", "Database error", 500)


def patch_task_submission(user, plan_id, task_id, payload):
    payload = validate_payload_object(payload)
    validate_allowed_fields(payload, PATCH_ALLOWED_FIELDS)
    note = normalize_note(payload, required=True)
    plan = get_plan_model_for_user(user, plan_id)
    task = (
        get_task_model_for_completed_plan_correction(user, plan_id, task_id)
        if plan.status == "completed"
        else get_task_model_for_submission(user, plan_id, task_id)
    )

    try:
        if plan.status == "completed":
            submission = task.submission
        else:
            submission, _ = ensure_submission(task, "in-progress", note="", completed_at=None)
        submission.note = note
        db.session.commit()
        return serialize_task(task)
    except TaskError:
        db.session.rollback()
        raise
    except SQLAlchemyError:
        db.session.rollback()
        raise TaskError("DATABASE_ERROR", "Database error", 500)


def complete_task_submission(user, plan_id, task_id, payload):
    payload = validate_payload_object(payload)
    if payload:
        validate_allowed_fields(payload, COMPLETE_ALLOWED_FIELDS)
    note = normalize_note(payload, required=False)
    task = get_task_model_for_submission(user, plan_id, task_id)

    try:
        submission, _ = ensure_submission(task, "completed", note="", completed_at=utc_now())
        if note is not None:
            submission.note = note
        elif submission.note is None:
            submission.note = ""
        if submission.status != "completed":
            submission.status = "completed"
            submission.completed_at = utc_now()
        elif submission.completed_at is None:
            submission.completed_at = utc_now()
        db.session.commit()
        return serialize_task(task)
    except TaskError:
        db.session.rollback()
        raise
    except SQLAlchemyError:
        db.session.rollback()
        raise TaskError("DATABASE_ERROR", "Database error", 500)
