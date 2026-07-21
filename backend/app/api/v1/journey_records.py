from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.auth import AuthError, get_user_by_identity
from app.services.children import ChildError
from app.services.journey_records import (
    JourneyRecordError,
    create_or_get_journey_record,
    finalize_journey_record,
    get_journey_record_model_for_plan,
    list_journey_record_models_for_user,
    serialize_journey_record,
    update_journey_record,
)
from app.services.plans import PlanError
from app.utils.responses import error_response, success_response


journey_records_bp = Blueprint("journey_records", __name__)


def current_user():
    return get_user_by_identity(get_jwt_identity())


def handle_error(error):
    return error_response(
        error.code,
        error.message,
        details=getattr(error, "details", {}),
        status_code=error.status_code,
    )


def validation_error(message):
    raise JourneyRecordError("VALIDATION_ERROR", message, 400)


def query_positive_integer(name):
    value = request.args.get(name)
    if value is None:
        return None
    if not value.isdecimal() or int(value) < 1:
        validation_error(f"{name} must be a positive integer")
    return int(value)


def query_limit():
    value = request.args.get("limit")
    if value is None:
        return 20
    if not value.isdecimal() or not 1 <= int(value) <= 100:
        validation_error("limit must be an integer from 1 to 100")
    return int(value)


def query_offset():
    value = request.args.get("offset")
    if value is None:
        return 0
    if not value.isdecimal():
        validation_error("offset must be a non-negative integer")
    return int(value)


def empty_body_only():
    payload = request.get_json(silent=True)
    if payload is None:
        if request.get_data(cache=True):
            validation_error("Request body must be empty or a JSON object")
        return
    if not isinstance(payload, dict) or payload:
        validation_error("Request body must be empty or a JSON object")


def json_object_body():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        validation_error("Request body must be a JSON object")
    return payload


@journey_records_bp.get("/journey-records")
@jwt_required()
def index():
    try:
        child_id = query_positive_integer("childId")
        status = request.args.get("status")
        if status is not None and status not in {"draft", "finalized"}:
            validation_error("status is invalid")
        limit = query_limit()
        offset = query_offset()
        records, total = list_journey_record_models_for_user(
            current_user(),
            child_id=child_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return success_response(
            data={
                "items": [serialize_journey_record(record, include_entries=False) for record in records],
                "total": total,
                "limit": limit,
                "offset": offset,
            },
            message="ok",
        )
    except (AuthError, ChildError, JourneyRecordError) as error:
        return handle_error(error)


@journey_records_bp.get("/plans/<int:plan_id>/journey-record")
@jwt_required()
def detail(plan_id):
    try:
        record = get_journey_record_model_for_plan(current_user(), plan_id)
        return success_response(data={"journeyRecord": serialize_journey_record(record)}, message="ok")
    except (AuthError, PlanError, JourneyRecordError) as error:
        return handle_error(error)


@journey_records_bp.post("/plans/<int:plan_id>/journey-record")
@jwt_required()
def create(plan_id):
    try:
        empty_body_only()
        record, created = create_or_get_journey_record(current_user(), plan_id)
        return success_response(
            data={"journeyRecord": serialize_journey_record(record), "created": created},
            message="Journey record created",
            status_code=201 if created else 200,
        )
    except (AuthError, PlanError, JourneyRecordError) as error:
        return handle_error(error)


@journey_records_bp.patch("/plans/<int:plan_id>/journey-record")
@jwt_required()
def update(plan_id):
    try:
        record = update_journey_record(current_user(), plan_id, json_object_body())
        return success_response(
            data={"journeyRecord": serialize_journey_record(record)},
            message="Journey record updated",
        )
    except (AuthError, PlanError, JourneyRecordError) as error:
        return handle_error(error)


@journey_records_bp.post("/plans/<int:plan_id>/journey-record/finalize")
@jwt_required()
def finalize(plan_id):
    try:
        empty_body_only()
        record, finalized_now = finalize_journey_record(current_user(), plan_id)
        return success_response(
            data={
                "journeyRecord": serialize_journey_record(record),
                "finalizedNow": finalized_now,
            },
            message="Journey record finalized",
        )
    except (AuthError, PlanError, JourneyRecordError) as error:
        return handle_error(error)
