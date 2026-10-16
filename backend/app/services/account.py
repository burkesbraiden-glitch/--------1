from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import (
    Child,
    ExplorationPlan,
    GuideAudioJob,
    GuideCard,
    JourneyRecord,
    PhoneVerificationCode,
    Route,
    RouteDay,
    RouteStop,
    Task,
    TaskSubmission,
    User,
)
from app.services.children import _guide_audio_key_is_controlled, cleanup_deleted_child_assets


class AccountError(Exception):
    def __init__(self, code, message, status_code):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _utc_datetime(value):
    return None if value is None else f"{value.isoformat()}Z"


def _date(value):
    return None if value is None else value.isoformat()


def _account_user(user):
    account = User.query.filter_by(id=user.id).with_for_update().first()
    if account is None:
        raise AccountError("UNAUTHORIZED", "Unauthorized", 401)
    return account


def _account_children(user_id):
    return Child.query.filter_by(user_id=user_id).order_by(Child.id.asc()).all()


def _account_plans(user_id):
    return ExplorationPlan.query.filter_by(user_id=user_id).order_by(ExplorationPlan.id.asc()).all()


def _account_routes(user_id):
    return Route.query.filter_by(user_id=user_id).order_by(Route.id.asc()).all()


def _query_for_ids(model, field, values):
    if not values:
        return []
    return model.query.filter(field.in_(values)).order_by(model.id.asc()).all()


def _serialize_user(user):
    return {
        "id": user.id,
        "nickname": user.nickname,
        "city": user.city,
        "createdAt": _utc_datetime(user.created_at),
        "updatedAt": _utc_datetime(user.updated_at),
    }


def _serialize_child(child):
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
        "createdAt": _utc_datetime(child.created_at),
        "updatedAt": _utc_datetime(child.updated_at),
    }


def _serialize_route(route):
    return {
        "id": route.id,
        "title": route.title,
        "city": route.city,
        "startDate": _date(route.start_date),
        "endDate": _date(route.end_date),
        "status": route.status,
        "createdAt": _utc_datetime(route.created_at),
        "updatedAt": _utc_datetime(route.updated_at),
    }


def _serialize_route_day(day):
    return {
        "id": day.id,
        "routeId": day.route_id,
        "dayNumber": day.day_number,
        "date": _date(day.date),
        "title": day.title,
        "createdAt": _utc_datetime(day.created_at),
        "updatedAt": _utc_datetime(day.updated_at),
    }


def _serialize_route_stop(stop):
    return {
        "id": stop.id,
        "routeDayId": stop.route_day_id,
        "attractionId": stop.attraction_id,
        "sortOrder": stop.sort_order,
        "note": stop.note,
        "createdAt": _utc_datetime(stop.created_at),
        "updatedAt": _utc_datetime(stop.updated_at),
    }


def _serialize_plan(plan):
    return {
        "id": plan.id,
        "childId": plan.child_id,
        "routeStopId": plan.route_stop_id,
        "title": plan.title,
        "destination": plan.destination,
        "ageGroup": plan.age_group,
        "duration": plan.duration,
        "interests": plan.interests or [],
        "status": plan.status,
        "completedAt": _utc_datetime(plan.completed_at),
        "createdAt": _utc_datetime(plan.created_at),
        "updatedAt": _utc_datetime(plan.updated_at),
    }


def _serialize_task(task):
    return {
        "id": task.id,
        "planId": task.plan_id,
        "sortOrder": task.sort_order,
        "title": task.title,
        "subtitle": task.subtitle,
        "ageGroup": task.age_group,
        "duration": task.duration,
        "taskType": task.task_type,
        "summary": task.summary,
        "objective": task.objective,
        "steps": task.steps or [],
        "questions": task.questions or [],
        "recordMode": task.record_mode,
        "theme": task.theme,
        "createdAt": _utc_datetime(task.created_at),
        "updatedAt": _utc_datetime(task.updated_at),
    }


def _serialize_submission(submission):
    return {
        "id": submission.id,
        "taskId": submission.task_id,
        "status": submission.status,
        "note": submission.note,
        "hasImage": bool(submission.image_url),
        "completedAt": _utc_datetime(submission.completed_at),
        "createdAt": _utc_datetime(submission.created_at),
        "updatedAt": _utc_datetime(submission.updated_at),
    }


def _serialize_guide_card(guide):
    return {
        "id": guide.id,
        "planId": guide.plan_id,
        "childIntro": guide.child_intro or [],
        "questions": guide.questions or [],
        "focusItems": guide.focus_items or [],
        "narrationText": guide.narration_text,
        "guideVersion": guide.guide_version,
        "audioStatus": guide.audio_status,
        "hasAudio": bool(guide.audio_object_key),
        "audioDurationSec": guide.audio_duration_sec,
        "audioGeneratedAt": _utc_datetime(guide.audio_generated_at),
        "createdAt": _utc_datetime(guide.created_at),
        "updatedAt": _utc_datetime(guide.updated_at),
    }


def _serialize_journey_record(record, has_images):
    return {
        "id": record.id,
        "planId": record.plan_id,
        "customTitle": record.custom_title,
        "summary": record.summary,
        "coverSubmissionId": record.cover_submission_id,
        "status": record.status,
        "hasImages": has_images,
        "finalizedAt": _utc_datetime(record.finalized_at),
        "createdAt": _utc_datetime(record.created_at),
        "updatedAt": _utc_datetime(record.updated_at),
    }


def export_account(user):
    """Build a current-user-only, transport-safe structured data copy."""
    children = _account_children(user.id)
    plans = _account_plans(user.id)
    routes = _account_routes(user.id)

    plan_ids = [plan.id for plan in plans]
    route_ids = [route.id for route in routes]
    tasks = _query_for_ids(Task, Task.plan_id, plan_ids)
    task_ids = [task.id for task in tasks]
    submissions = _query_for_ids(TaskSubmission, TaskSubmission.task_id, task_ids)
    guides = _query_for_ids(GuideCard, GuideCard.plan_id, plan_ids)
    records = _query_for_ids(JourneyRecord, JourneyRecord.plan_id, plan_ids)
    days = _query_for_ids(RouteDay, RouteDay.route_id, route_ids)
    day_ids = [day.id for day in days]
    stops = _query_for_ids(RouteStop, RouteStop.route_day_id, day_ids)

    task_plan_ids = {task.id: task.plan_id for task in tasks}
    plans_with_images = {
        task_plan_ids[submission.task_id]
        for submission in submissions
        if submission.image_url and submission.task_id in task_plan_ids
    }

    return {
        "formatVersion": "p11.2c",
        "user": _serialize_user(user),
        "children": [_serialize_child(child) for child in children],
        "routes": [_serialize_route(route) for route in routes],
        "routeDays": [_serialize_route_day(day) for day in days],
        "routeStops": [_serialize_route_stop(stop) for stop in stops],
        "plans": [_serialize_plan(plan) for plan in plans],
        "tasks": [_serialize_task(task) for task in tasks],
        "taskSubmissions": [_serialize_submission(submission) for submission in submissions],
        "guideCards": [_serialize_guide_card(guide) for guide in guides],
        "journeyRecords": [
            _serialize_journey_record(record, record.plan_id in plans_with_images)
            for record in records
        ],
    }


def delete_account(user, *, audio_storage=None):
    """Delete only the authenticated user's data, then clean unreferenced assets."""
    account = _account_user(user)
    children = _account_children(account.id)
    plans = _account_plans(account.id)
    routes = _account_routes(account.id)

    plan_ids = [plan.id for plan in plans]
    route_ids = [route.id for route in routes]
    tasks = _query_for_ids(Task, Task.plan_id, plan_ids)
    task_ids = [task.id for task in tasks]
    submissions = _query_for_ids(TaskSubmission, TaskSubmission.task_id, task_ids)
    records = _query_for_ids(JourneyRecord, JourneyRecord.plan_id, plan_ids)
    guides = _query_for_ids(GuideCard, GuideCard.plan_id, plan_ids)
    guide_ids = [guide.id for guide in guides]
    jobs = _query_for_ids(GuideAudioJob, GuideAudioJob.guide_id, guide_ids)
    days = _query_for_ids(RouteDay, RouteDay.route_id, route_ids)
    day_ids = [day.id for day in days]
    stops = _query_for_ids(RouteStop, RouteStop.route_day_id, day_ids)
    verification_code = (
        db.session.get(PhoneVerificationCode, account.phone) if account.phone else None
    )

    task_image_keys = tuple(
        sorted({item.image_url for item in submissions if isinstance(item.image_url, str) and item.image_url})
    )
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
        for stop in stops:
            db.session.delete(stop)
        db.session.flush()
        for day in days:
            db.session.delete(day)
        db.session.flush()
        for route in routes:
            db.session.delete(route)
        db.session.flush()
        for child in children:
            db.session.delete(child)
        db.session.flush()
        if verification_code is not None:
            db.session.delete(verification_code)
            db.session.flush()
        db.session.delete(account)
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        raise AccountError("DATABASE_ERROR", "Database error", 500) from error

    cleanup_deleted_child_assets(
        task_image_keys=task_image_keys,
        record_ids=record_ids,
        guide_audio_keys=guide_audio_keys,
        audio_storage=audio_storage,
    )
    return {"deleted": True}
