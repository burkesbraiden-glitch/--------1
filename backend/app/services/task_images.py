import os
from pathlib import Path
from uuid import uuid4

from flask import current_app
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import TaskSubmission
from app.services.task_submissions import (
    get_task_model_for_submission,
    next_sqlite_submission_id,
)
from app.services.tasks import TaskError, serialize_task


IMAGE_TYPES = {
    "png": {"extension": ".png", "content_type": "image/png"},
    "jpeg": {"extension": ".jpg", "content_type": "image/jpeg"},
    "webp": {"extension": ".webp", "content_type": "image/webp"},
}


def upload_dir():
    return Path(current_app.config["TASK_IMAGE_UPLOAD_DIR"])


def read_upload_bytes(file_storage):
    if file_storage is None or not file_storage.filename:
        raise TaskError("IMAGE_REQUIRED", "Image is required", 400)

    max_bytes = int(current_app.config["TASK_IMAGE_MAX_BYTES"])
    data = file_storage.stream.read(max_bytes + 1)
    if not data:
        raise TaskError("IMAGE_REQUIRED", "Image is required", 400)
    if len(data) > max_bytes:
        raise TaskError("IMAGE_TOO_LARGE", "Image is too large", 413)
    return data


def detect_image_type(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    raise TaskError("UNSUPPORTED_IMAGE_TYPE", "Unsupported image type", 400)


def new_storage_key(image_type):
    return f"task-images/{uuid4().hex}{IMAGE_TYPES[image_type]['extension']}"


def path_for_storage_key(storage_key):
    if not storage_key or not storage_key.startswith("task-images/"):
        raise TaskError("TASK_IMAGE_NOT_FOUND", "Task image not found", 404)
    filename = storage_key.removeprefix("task-images/")
    if not filename or "/" in filename or "\\" in filename:
        raise TaskError("TASK_IMAGE_NOT_FOUND", "Task image not found", 404)

    root = upload_dir().resolve()
    candidate = (root / filename).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise TaskError("TASK_IMAGE_NOT_FOUND", "Task image not found", 404) from exc
    return candidate


def write_image_file(storage_key, data):
    final_path = path_for_storage_key(storage_key)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = final_path.with_name(f".{final_path.name}.{uuid4().hex}.tmp")
    try:
        temp_path.write_bytes(data)
        os.replace(temp_path, final_path)
        return final_path
    except Exception:
        cleanup_file(temp_path)
        cleanup_file(final_path)
        raise


def cleanup_file(path):
    try:
        path = Path(path)
        if path.exists():
            path.unlink()
    except OSError:
        current_app.logger.warning("Failed to remove task image file")


def get_or_create_submission(task):
    if task.submission is not None:
        return task.submission

    submission = TaskSubmission(
        id=next_sqlite_submission_id(),
        task_id=task.id,
        status="in-progress",
        image_url=None,
        note="",
        completed_at=None,
    )
    db.session.add(submission)
    try:
        db.session.flush()
        task.submission = submission
        return submission
    except IntegrityError:
        db.session.rollback()
        task = get_task_model_for_submission(
            task.plan.user,
            task.plan_id,
            task.id,
            validate_plan_status=True,
        )
        if task.submission is None:
            raise TaskError("DATABASE_ERROR", "Database error", 500)
        return task.submission


def save_task_image(user, plan_id, task_id, file_storage):
    task = get_task_model_for_submission(user, plan_id, task_id, validate_plan_status=True)
    data = read_upload_bytes(file_storage)
    image_type = detect_image_type(data)
    storage_key = new_storage_key(image_type)
    new_path = None
    old_path = None

    try:
        new_path = write_image_file(storage_key, data)
        submission = get_or_create_submission(task)
        old_key = submission.image_url
        if old_key:
            try:
                old_path = path_for_storage_key(old_key)
            except TaskError:
                old_path = None
        submission.image_url = storage_key
        db.session.commit()
    except TaskError:
        db.session.rollback()
        if new_path is not None:
            cleanup_file(new_path)
        raise
    except (SQLAlchemyError, Exception) as exc:
        db.session.rollback()
        if new_path is not None:
            cleanup_file(new_path)
        raise TaskError("DATABASE_ERROR", "Database error", 500) from exc

    if old_path is not None and old_path != new_path:
        cleanup_file(old_path)

    return serialize_task(task)


def get_task_image_file(user, plan_id, task_id):
    task = get_task_model_for_submission(user, plan_id, task_id, validate_plan_status=False)
    submission = task.submission
    if submission is None or not submission.image_url:
        raise TaskError("TASK_IMAGE_NOT_FOUND", "Task image not found", 404)

    image_path = path_for_storage_key(submission.image_url)
    if not image_path.is_file():
        raise TaskError("TASK_IMAGE_NOT_FOUND", "Task image not found", 404)

    with image_path.open("rb") as image_file:
        image_type = detect_image_type(image_file.read(16))
    return image_path, IMAGE_TYPES[image_type]["content_type"]
