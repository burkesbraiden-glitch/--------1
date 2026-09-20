from flask import Blueprint
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.auth import AuthError, get_user_by_identity
from app.services.guide_audio import (
    GuideAudioError,
    GuideAudioService,
    request_audio_generation_with_job,
)
from app.services.guides import GuideError, generate_guide, get_guide
from app.services.plans import PlanError
from app.utils.responses import error_response, success_response


guides_bp = Blueprint("guides", __name__)


def current_user():
    return get_user_by_identity(get_jwt_identity())


def handle_error(error):
    return error_response(error.code, error.message, status_code=error.status_code)


@guides_bp.get("/<int:plan_id>/guide")
@jwt_required()
def detail(plan_id):
    try:
        return success_response(data={"guide": get_guide(current_user(), plan_id)}, message="ok")
    except (AuthError, GuideError, GuideAudioError, PlanError) as error:
        return handle_error(error)


@guides_bp.post("/<int:plan_id>/guide/generate")
@jwt_required()
def generate(plan_id):
    try:
        guide, created = generate_guide(current_user(), plan_id)
        status_code = 201 if created else 200
        return success_response(data={"guide": guide}, message="Guide generated", status_code=status_code)
    except (AuthError, GuideError, GuideAudioError, PlanError) as error:
        return handle_error(error)


@guides_bp.post("/<int:plan_id>/guide/audio/retry")
@jwt_required()
def retry_audio(plan_id):
    try:
        request_audio_generation_with_job(user=current_user(), plan_id=plan_id, retry=True)
        return success_response(data={"guide": get_guide(current_user(), plan_id)}, message="Audio generation retried")
    except (AuthError, GuideError, GuideAudioError, PlanError) as error:
        return handle_error(error)


@guides_bp.post("/<int:plan_id>/guide/audio/request")
@jwt_required()
def request_audio(plan_id):
    try:
        _intent, job, job_created = request_audio_generation_with_job(
            user=current_user(),
            plan_id=plan_id,
        )
        return success_response(
            data={
                "audioStatus": "pending",
                "created": job_created,
                "jobStatus": job.status,
            },
            message="Audio generation requested",
            status_code=202,
        )
    except (AuthError, GuideError, GuideAudioError, PlanError) as error:
        return handle_error(error)
