from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import joinedload

from app.constants import EXPECTED_TASK_COUNT
from app.extensions import db
from app.models import Task
from app.services.plans import PlanError, format_datetime, get_plan_model_for_user
from app.services.task_generator import generate_task_definitions


ALLOWED_GENERATE_STATUSES = {"ready", "in-progress"}


class TaskError(Exception):
    def __init__(self, code, message, status_code, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def serialize_task(task):
    submission = task.submission
    record = {"imageUrl": None, "note": ""}
    if submission is not None:
        image_url = None
        if submission.image_url:
            image_url = f"/api/v1/plans/{task.plan_id}/tasks/{task.id}/submission/image"
        record = {
            "imageUrl": image_url,
            "note": submission.note or "",
        }

    return {
        "id": task.id,
        "planId": task.plan_id,
        "order": task.sort_order,
        "title": task.title,
        "subtitle": task.subtitle,
        "status": submission.status if submission is not None else "not-started",
        "ageGroup": task.age_group,
        "duration": task.duration,
        "type": task.task_type,
        "summary": task.summary,
        "objective": task.objective,
        "steps": task.steps or [],
        "questions": task.questions or [],
        "recordMode": task.record_mode,
        "theme": task.theme,
        "record": record,
        "completedAt": format_datetime(submission.completed_at) if submission is not None else None,
        "createdAt": format_datetime(task.created_at),
        "updatedAt": format_datetime(task.updated_at),
    }


def task_query_for_plan(plan_id):
    return (
        Task.query.options(joinedload(Task.submission))
        .filter_by(plan_id=plan_id)
        .order_by(Task.sort_order.asc())
    )


def get_task_models_for_plan(plan):
    return task_query_for_plan(plan.id).all()


def ensure_complete_task_set(tasks):
    if tasks and len(tasks) != EXPECTED_TASK_COUNT:
        raise TaskError(
            "TASK_SET_INCOMPLETE",
            "Task set is incomplete",
            409,
            {"expectedCount": EXPECTED_TASK_COUNT, "actualCount": len(tasks)},
        )


def list_tasks(user, plan_id):
    plan = get_plan_model_for_user(user, plan_id)
    tasks = get_task_models_for_plan(plan)
    return {
        "tasks": [serialize_task(task) for task in tasks],
        "taskCount": len(tasks),
    }


def sqlite_next_task_ids(count):
    if db.engine.dialect.name != "sqlite":
        return [None] * count
    max_id = db.session.query(db.func.max(Task.id)).scalar() or 0
    return list(range(max_id + 1, max_id + count + 1))


def build_task(plan, task_definition, task_id=None):
    return Task(
        id=task_id,
        plan_id=plan.id,
        sort_order=task_definition["sort_order"],
        title=task_definition["title"],
        subtitle=task_definition["subtitle"],
        age_group=task_definition["age_group"],
        duration=task_definition["duration"],
        task_type=task_definition["task_type"],
        summary=task_definition["summary"],
        objective=task_definition["objective"],
        steps=task_definition["steps"],
        questions=task_definition["questions"],
        record_mode=task_definition["record_mode"],
        theme=task_definition["theme"],
    )


def generate_tasks(user, plan_id):
    plan = get_plan_model_for_user(user, plan_id)
    if plan.status == "draft":
        raise TaskError("PLAN_NOT_READY", "Plan not ready", 409)
    if plan.status == "completed":
        raise TaskError("PLAN_ALREADY_COMPLETED", "Plan already completed", 409)
    if plan.status not in ALLOWED_GENERATE_STATUSES:
        raise TaskError("PLAN_NOT_READY", "Plan not ready", 409)

    existing_tasks = get_task_models_for_plan(plan)
    ensure_complete_task_set(existing_tasks)
    if existing_tasks:
        return {
            "tasks": [serialize_task(task) for task in existing_tasks],
            "taskCount": len(existing_tasks),
        }, False

    definitions = generate_task_definitions(plan)
    task_ids = sqlite_next_task_ids(len(definitions))
    tasks = [build_task(plan, definition, task_id) for definition, task_id in zip(definitions, task_ids)]

    try:
        db.session.add_all(tasks)
        db.session.commit()
        created_tasks = get_task_models_for_plan(plan)
        return {
            "tasks": [serialize_task(task) for task in created_tasks],
            "taskCount": len(created_tasks),
        }, True
    except IntegrityError:
        db.session.rollback()
        existing_tasks = get_task_models_for_plan(plan)
        ensure_complete_task_set(existing_tasks)
        if existing_tasks:
            return {
                "tasks": [serialize_task(task) for task in existing_tasks],
                "taskCount": len(existing_tasks),
            }, False
        raise TaskError("DATABASE_ERROR", "Database error", 500)
    except SQLAlchemyError:
        db.session.rollback()
        raise TaskError("DATABASE_ERROR", "Database error", 500)


def get_task(user, plan_id, task_id):
    get_plan_model_for_user(user, plan_id)
    task = (
        Task.query.options(joinedload(Task.submission))
        .filter_by(id=task_id, plan_id=plan_id)
        .first()
    )
    if task is None:
        raise TaskError("TASK_NOT_FOUND", "Task not found", 404)
    return serialize_task(task)
