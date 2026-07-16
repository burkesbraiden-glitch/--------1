from flask import Blueprint, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.auth import AuthError, get_user_by_identity
from app.services.plans import PlanError
from app.services.task_submissions import (
    complete_task_submission,
    patch_task_submission,
    start_task_submission,
)
from app.services.task_images import get_task_image_file, save_task_image
from app.services.tasks import TaskError, generate_tasks, get_task, list_tasks
from app.utils.responses import error_response, success_response


tasks_bp = Blueprint("tasks", __name__)


def current_user():
    return get_user_by_identity(get_jwt_identity())


def handle_error(error):
    details = getattr(error, "details", {})
    return error_response(error.code, error.message, details=details, status_code=error.status_code)


@tasks_bp.get("/<int:plan_id>/tasks")
@jwt_required()
def index(plan_id):
    try:
        return success_response(data=list_tasks(current_user(), plan_id), message="ok")
    except (AuthError, PlanError, TaskError) as error:
        return handle_error(error)


@tasks_bp.post("/<int:plan_id>/tasks/generate")
@jwt_required()
def generate(plan_id):
    try:
        data, created = generate_tasks(current_user(), plan_id)
        status_code = 201 if created else 200
        return success_response(data=data, message="Tasks generated", status_code=status_code)
    except (AuthError, PlanError, TaskError) as error:
        return handle_error(error)


@tasks_bp.get("/<int:plan_id>/tasks/<int:task_id>")
@jwt_required()
def detail(plan_id, task_id):
    try:
        return success_response(data={"task": get_task(current_user(), plan_id, task_id)}, message="ok")
    except (AuthError, PlanError, TaskError) as error:
        return handle_error(error)


@tasks_bp.post("/<int:plan_id>/tasks/<int:task_id>/submission/start")
@jwt_required()
def start_submission(plan_id, task_id):
    try:
        task, created = start_task_submission(current_user(), plan_id, task_id)
        status_code = 201 if created else 200
        return success_response(
            data={"task": task},
            message="Task started",
            status_code=status_code,
        )
    except (AuthError, PlanError, TaskError) as error:
        return handle_error(error)


@tasks_bp.patch("/<int:plan_id>/tasks/<int:task_id>/submission")
@jwt_required()
def patch_submission(plan_id, task_id):
    try:
        task = patch_task_submission(current_user(), plan_id, task_id, request.get_json(silent=True))
        return success_response(data={"task": task}, message="Task submission updated")
    except (AuthError, PlanError, TaskError) as error:
        return handle_error(error)


@tasks_bp.post("/<int:plan_id>/tasks/<int:task_id>/submission/complete")
@jwt_required()
def complete_submission(plan_id, task_id):
    try:
        task = complete_task_submission(current_user(), plan_id, task_id, request.get_json(silent=True))
        return success_response(data={"task": task}, message="Task completed")
    except (AuthError, PlanError, TaskError) as error:
        return handle_error(error)


@tasks_bp.post("/<int:plan_id>/tasks/<int:task_id>/submission/image")
@jwt_required()
def upload_submission_image(plan_id, task_id):
    try:
        task = save_task_image(current_user(), plan_id, task_id, request.files.get("image"))
        return success_response(data={"task": task}, message="Task image saved")
    except (AuthError, PlanError, TaskError) as error:
        return handle_error(error)


@tasks_bp.get("/<int:plan_id>/tasks/<int:task_id>/submission/image")
@jwt_required()
def get_submission_image(plan_id, task_id):
    try:
        image_path, content_type = get_task_image_file(current_user(), plan_id, task_id)
        response = send_file(image_path, mimetype=content_type, as_attachment=False)
        response.headers["Cache-Control"] = "private"
        response.headers["Content-Disposition"] = f"inline; filename={image_path.name}"
        return response
    except (AuthError, PlanError, TaskError) as error:
        return handle_error(error)
