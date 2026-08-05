from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.constants import EXPECTED_TASK_COUNT
from app.extensions import db
from app.models import Child, ExplorationPlan, Task
from app.services.children import normalize_interests
from app.utils.time import utc_now


CREATE_FORBIDDEN_FIELDS = {
    "id",
    "userId",
    "status",
    "taskCount",
    "taskIds",
    "createdAt",
    "updatedAt",
}
PATCH_ALLOWED_FIELDS = {"title", "destination", "duration", "interests"}


class PlanError(Exception):
    def __init__(self, code, message, status_code, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def format_datetime(value):
    if value is None:
        return None
    return f"{value.isoformat()}Z"


def serialize_plan(plan):
    return {
        "id": plan.id,
        "title": plan.title,
        "destination": plan.destination,
        "ageGroup": plan.age_group,
        "duration": plan.duration,
        "taskCount": len(plan.tasks or []),
        "interests": plan.interests or [],
        "status": plan.status,
        "childId": plan.child_id,
        "completedAt": format_datetime(plan.completed_at),
        "createdAt": format_datetime(plan.created_at),
        "updatedAt": format_datetime(plan.updated_at),
    }


def normalize_required_string(payload, field_name, max_length):
    value = payload.get(field_name)
    if not isinstance(value, str):
        raise PlanError("VALIDATION_ERROR", f"{field_name} is required", 400)
    value = value.strip()
    if not 1 <= len(value) <= max_length:
        raise PlanError(
            "VALIDATION_ERROR",
            f"{field_name} must be 1 to {max_length} characters",
            400,
        )
    return value


def validate_no_forbidden_fields(payload, forbidden_fields):
    if set(payload) & forbidden_fields:
        raise PlanError("VALIDATION_ERROR", "Forbidden field", 400)


def normalize_child_id(payload):
    if "childId" not in payload:
        return None
    child_id = payload["childId"]
    if isinstance(child_id, bool) or not isinstance(child_id, int) or child_id <= 0:
        raise PlanError("VALIDATION_ERROR", "childId must be a positive integer", 400)
    return child_id


def child_query(user):
    return Child.query.filter_by(user_id=user.id)


def select_default_child(user):
    children = child_query(user).order_by(Child.is_default.desc(), Child.created_at.asc()).all()
    if not children:
        raise PlanError(
            "CHILD_REQUIRED",
            "创建探索计划前，请先完善孩子档案。",
            409,
        )
    return children[0]


def get_child_for_plan(user, payload):
    child_id = normalize_child_id(payload)
    if child_id is None:
        child = select_default_child(user)
    else:
        child = Child.query.filter_by(id=child_id, user_id=user.id).first()
        if child is None:
            raise PlanError("CHILD_NOT_FOUND", "Child not found", 404)

    if "ageGroup" not in payload:
        return child, child.age_group
    age_group = payload["ageGroup"]
    if not isinstance(age_group, str):
        raise PlanError("VALIDATION_ERROR", "ageGroup must be a string", 400)
    if age_group != child.age_group:
        raise PlanError("VALIDATION_ERROR", "ageGroup does not match child", 400)
    return child, age_group


def validate_create_payload(payload):
    validate_no_forbidden_fields(payload, CREATE_FORBIDDEN_FIELDS)
    destination = normalize_required_string(payload, "destination", 120)
    raw_title = payload.get("title")
    if raw_title is None:
        title = f"{destination}亲子探索"
    elif not isinstance(raw_title, str):
        raise PlanError("VALIDATION_ERROR", "title must be a string", 400)
    else:
        title = raw_title.strip() or f"{destination}亲子探索"

    if len(title) > 120:
        raise PlanError(
            "VALIDATION_ERROR",
            "title must be 1 to 120 characters",
            400,
        )

    return {
        "title": title,
        "destination": destination,
        "duration": normalize_required_string(payload, "duration", 32),
        "interests": normalize_interests(payload),
    }


def get_plan_model_for_user(user, plan_id):
    plan = (
        ExplorationPlan.query.options(selectinload(ExplorationPlan.tasks))
        .filter_by(id=plan_id, user_id=user.id)
        .first()
    )
    if plan is None:
        raise PlanError("PLAN_NOT_FOUND", "Plan not found", 404)
    return plan


def list_plans(user):
    plans = (
        ExplorationPlan.query.options(selectinload(ExplorationPlan.tasks))
        .filter_by(user_id=user.id)
        .order_by(ExplorationPlan.updated_at.desc(), ExplorationPlan.created_at.desc())
        .all()
    )
    return {"plans": [serialize_plan(plan) for plan in plans]}


def get_plan(user, plan_id):
    return serialize_plan(get_plan_model_for_user(user, plan_id))


def create_plan(user, payload):
    values = validate_create_payload(payload)
    child, age_group = get_child_for_plan(user, payload)

    try:
        plan = ExplorationPlan(
            user_id=user.id,
            child_id=child.id,
            title=values["title"],
            destination=values["destination"],
            age_group=age_group,
            duration=values["duration"],
            interests=values["interests"],
            status="ready",
        )
        db.session.add(plan)
        db.session.commit()
        db.session.refresh(plan)
        return serialize_plan(plan)
    except SQLAlchemyError:
        db.session.rollback()
        raise PlanError("DATABASE_ERROR", "Database error", 500)


def validate_patch_payload(payload):
    if not payload:
        raise PlanError("VALIDATION_ERROR", "Request body must not be empty", 400)
    if set(payload) - PATCH_ALLOWED_FIELDS:
        raise PlanError("VALIDATION_ERROR", "Unknown field", 400)


def update_plan(user, plan_id, payload):
    plan = get_plan_model_for_user(user, plan_id)
    if plan.status == "completed":
        raise PlanError("PLAN_ALREADY_COMPLETED", "Plan already completed", 409)
    validate_patch_payload(payload)

    try:
        if "title" in payload:
            plan.title = normalize_required_string(payload, "title", 120)
        if "destination" in payload:
            plan.destination = normalize_required_string(payload, "destination", 120)
        if "duration" in payload:
            plan.duration = normalize_required_string(payload, "duration", 32)
        if "interests" in payload:
            plan.interests = normalize_interests(payload, plan.interests or [])
        db.session.commit()
        return serialize_plan(plan)
    except SQLAlchemyError:
        db.session.rollback()
        raise PlanError("DATABASE_ERROR", "Database error", 500)


def start_plan(user, plan_id):
    plan = get_plan_model_for_user(user, plan_id)

    if plan.status == "completed":
        raise PlanError("PLAN_ALREADY_COMPLETED", "Plan already completed", 409)
    if plan.status == "draft":
        raise PlanError("PLAN_NOT_READY", "Plan not ready", 409)
    if plan.status == "in-progress":
        return serialize_plan(plan)

    try:
        plan.status = "in-progress"
        db.session.commit()
        return serialize_plan(plan)
    except SQLAlchemyError:
        db.session.rollback()
        raise PlanError("DATABASE_ERROR", "Database error", 500)


def _get_plan_for_completion(user, plan_id):
    plan = (
        ExplorationPlan.query.filter_by(id=plan_id, user_id=user.id)
        .with_for_update()
        .first()
    )
    if plan is None:
        raise PlanError("PLAN_NOT_FOUND", "Plan not found", 404)
    return plan


def _completion_details(tasks):
    missing_submission_task_ids = [task.id for task in tasks if task.submission is None]
    incomplete_task_ids = [
        task.id
        for task in tasks
        if task.submission is not None and task.submission.status != "completed"
    ]
    completed_task_count = sum(
        task.submission is not None and task.submission.status == "completed"
        for task in tasks
    )
    return {
        "expectedTaskCount": EXPECTED_TASK_COUNT,
        "taskCount": len(tasks),
        "completedTaskCount": completed_task_count,
        "missingSubmissionTaskIds": missing_submission_task_ids,
        "incompleteTaskIds": incomplete_task_ids,
    }


def complete_plan(user, plan_id):
    plan = _get_plan_for_completion(user, plan_id)

    if plan.status == "completed":
        return serialize_plan(plan), False
    if plan.status == "draft":
        raise PlanError("PLAN_NOT_READY", "Plan not ready", 409)
    if plan.status == "ready":
        raise PlanError("PLAN_NOT_STARTED", "Plan not started", 409)
    if plan.status != "in-progress":
        raise PlanError("PLAN_NOT_READY", "Plan not ready", 409)

    tasks = (
        Task.query.options(selectinload(Task.submission))
        .filter_by(plan_id=plan.id)
        .order_by(Task.sort_order.asc(), Task.id.asc())
        .all()
    )
    details = _completion_details(tasks)
    if (
        details["taskCount"] != EXPECTED_TASK_COUNT
        or details["missingSubmissionTaskIds"]
        or details["incompleteTaskIds"]
    ):
        raise PlanError("PLAN_TASKS_INCOMPLETE", "Plan tasks are incomplete", 409, details)

    try:
        plan.status = "completed"
        plan.completed_at = utc_now()
        db.session.commit()
        return serialize_plan(plan), True
    except SQLAlchemyError:
        db.session.rollback()
        raise PlanError("DATABASE_ERROR", "Database error", 500)
