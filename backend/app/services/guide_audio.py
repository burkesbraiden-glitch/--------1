from dataclasses import dataclass
import re
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import GuideCard
from flask import current_app

from app.services.audio_storage import AudioStorageError, UnconfiguredAudioStorage, create_audio_storage
from app.services.guide_narration import NarrationError, build_audio_source_hash, build_narration_text
from app.services.plans import get_plan_model_for_user
from app.services.tts_provider import UnconfiguredTTSProvider
from app.utils.time import utc_now


AUDIO_STATUSES = {"none", "pending", "generating", "ready", "failed"}
AUDIO_LANGUAGE = "zh-CN"
AUDIO_VOICE_PROFILE_ID = "warm-guide-v1"
TTS_CONFIG_VERSION = "p8-2b2-edge-v1"
AUDIO_OUTPUT_FORMAT = "mp3"
SIGNED_URL_TTL_SECONDS = 300
_SHA256_VALUE_PATTERN = re.compile(r"\b[0-9a-fA-F]{64}\b")
_GENERATION_TOKEN_PATTERN = re.compile(r"\b[0-9a-fA-F]{32}\b")
_DATABASE_MESSAGE_MAX_LENGTH = 512


class GuideAudioError(Exception):
    def __init__(self, code, message, status_code):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class AudioGenerationIntent:
    guide_id: int
    guide_version: int
    source_hash: str
    generation_token: str
    created: bool


@dataclass(frozen=True)
class AudioGenerationResult:
    status: str


def _same_generation(guide, job):
    return (
        guide.id == job.guide_id
        and guide.guide_version == job.guide_version
        and guide.audio_source_hash == job.source_hash
        and guide.audio_generation_token == job.generation_token
    )


def _result_value(result, name):
    if isinstance(result, dict):
        return result.get(name)
    return getattr(result, name, None)


def _controlled_error_code(error, fallback):
    code = getattr(error, "code", None)
    if isinstance(code, str) and code and code.isupper() and len(code) <= 64:
        return code
    return fallback


def _set_diagnostic_phase(phase_callback, phase):
    if phase_callback is not None:
        phase_callback(phase)


def _redact_database_message(value, sensitive_values=()):
    if value is None:
        return None

    message = str(value)
    for sensitive_value in sensitive_values:
        if isinstance(sensitive_value, str) and sensitive_value:
            message = message.replace(sensitive_value, "<redacted>")
    message = _SHA256_VALUE_PATTERN.sub("<redacted-sha256>", message)
    message = _GENERATION_TOKEN_PATTERN.sub("<redacted-token>", message)
    return message[:_DATABASE_MESSAGE_MAX_LENGTH]


def _log_audio_database_error(error, *, phase, plan_id, guide_id, sensitive_values=()):
    dbapi_error = getattr(error, "orig", None)
    dbapi_args = getattr(dbapi_error, "args", ()) if dbapi_error is not None else ()
    if not isinstance(dbapi_args, (tuple, list)):
        dbapi_args = (dbapi_args,)

    mysql_error_code = dbapi_args[0] if dbapi_args and isinstance(dbapi_args[0], int) else None
    if len(dbapi_args) > 1:
        mysql_error_message = dbapi_args[1]
    elif dbapi_args and not isinstance(dbapi_args[0], int):
        mysql_error_message = dbapi_args[0]
    else:
        mysql_error_message = str(dbapi_error) if dbapi_error is not None else None

    current_app.logger.error(
        "guide_audio_database_error phase=%s plan_id=%s guide_id=%s "
        "sqlalchemy_exception=%s dbapi_exception=%s mysql_error_code=%s mysql_error_message=%s",
        phase,
        plan_id,
        guide_id,
        type(error).__name__,
        type(dbapi_error).__name__ if dbapi_error is not None else None,
        mysql_error_code,
        _redact_database_message(mysql_error_message, sensitive_values),
    )


class GuideAudioService:
    def __init__(self, *, tts_provider=None, storage=None):
        self.tts_provider = tts_provider or UnconfiguredTTSProvider()
        if storage is not None:
            self.storage = storage
        else:
            try:
                self.storage = create_audio_storage(current_app.config)
            except RuntimeError:
                self.storage = UnconfiguredAudioStorage()

    def _get_owned_guide(self, *, user, plan_id):
        plan = get_plan_model_for_user(user, plan_id)
        guide = GuideCard.query.filter_by(plan_id=plan.id).with_for_update().first()
        if guide is None:
            raise GuideAudioError("GUIDE_NOT_FOUND", "Guide not found", 404)
        return plan, guide

    def _build_current_narration(self, *, plan, guide):
        try:
            return build_narration_text(plan=plan, guide=guide)
        except NarrationError as error:
            raise GuideAudioError(error.code, error.message, 409) from error

    def _source_hash(self, narration_text):
        return build_audio_source_hash(
            narration_text=narration_text,
            language=AUDIO_LANGUAGE,
            voice_profile_id=AUDIO_VOICE_PROFILE_ID,
            tts_config_version=TTS_CONFIG_VERSION,
            output_format=AUDIO_OUTPUT_FORMAT,
        )

    def _invalidate_audio(self, guide):
        old_object_key = guide.audio_object_key
        guide.audio_status = "pending"
        guide.audio_object_key = None
        guide.audio_duration_sec = None
        guide.audio_generated_at = None
        guide.audio_error_code = None
        if old_object_key:
            try:
                self.storage.delete(object_key=old_object_key)
            except Exception:
                # The asset is already unreachable through the Guide API. A future worker
                # can reconcile an orphan without allowing stale audio to become public.
                pass

    def _intent_from_guide(self, guide, *, created):
        return AudioGenerationIntent(
            guide_id=guide.id,
            guide_version=guide.guide_version,
            source_hash=guide.audio_source_hash,
            generation_token=guide.audio_generation_token,
            created=created,
        )

    def validate_audio_state(self, guide):
        status = guide.audio_status or "none"
        if status not in AUDIO_STATUSES:
            raise GuideAudioError("AUDIO_STATE_INVALID", "Audio state is invalid", 409)
        if status == "ready" and (not guide.audio_object_key or not guide.audio_source_hash):
            raise GuideAudioError("AUDIO_STATE_INVALID", "Ready audio is incomplete", 409)
        return status

    def _persist_request(self, *, guide, created, commit, phase_callback=None):
        _set_diagnostic_phase(phase_callback, "guide_commit" if commit else "guide_flush")
        if commit:
            db.session.commit()
        else:
            db.session.flush()
        return self._intent_from_guide(guide, created=created)

    def request_audio_generation(
        self,
        *,
        user,
        plan_id,
        retry=False,
        commit=True,
        phase_callback=None,
        guide_id_callback=None,
    ):
        _set_diagnostic_phase(phase_callback, "owned_guide_lookup")
        plan, guide = self._get_owned_guide(user=user, plan_id=plan_id)
        if guide_id_callback is not None:
            guide_id_callback(guide.id)
        current_status = self.validate_audio_state(guide)
        if retry and current_status != "failed":
            if commit:
                db.session.rollback()
            raise GuideAudioError(
                "AUDIO_RETRY_NOT_ALLOWED",
                "Audio retry is only allowed after an audio failure",
                409,
            )

        _set_diagnostic_phase(phase_callback, "guide_preparation")
        narration_text = self._build_current_narration(plan=plan, guide=guide)
        source_hash = self._source_hash(narration_text)
        narration_changed = guide.narration_text != narration_text

        if narration_changed:
            guide.narration_text = narration_text
            has_audio_generation = bool(
                guide.audio_source_hash
                or guide.audio_generation_token
                or guide.audio_object_key
                or guide.audio_status != "none"
            )
            if has_audio_generation:
                guide.guide_version = (guide.guide_version or 1) + 1
                self._invalidate_audio(guide)

        status = self.validate_audio_state(guide)
        same_source = guide.audio_source_hash == source_hash

        if retry:
            guide.audio_status = "pending"
            guide.audio_source_hash = source_hash
            guide.audio_generation_token = uuid4().hex
            guide.audio_object_key = None
            guide.audio_duration_sec = None
            guide.audio_generated_at = None
            guide.audio_error_code = None
            return self._persist_request(
                guide=guide,
                created=True,
                commit=commit,
                phase_callback=phase_callback,
            )

        if same_source and status in {"pending", "generating", "ready", "failed"} and guide.audio_generation_token:
            return self._persist_request(
                guide=guide,
                created=False,
                commit=commit,
                phase_callback=phase_callback,
            )

        guide.narration_text = narration_text
        guide.audio_status = "pending"
        guide.audio_source_hash = source_hash
        guide.audio_generation_token = uuid4().hex
        guide.audio_object_key = None
        guide.audio_duration_sec = None
        guide.audio_generated_at = None
        guide.audio_error_code = None
        return self._persist_request(
            guide=guide,
            created=True,
            commit=commit,
            phase_callback=phase_callback,
        )

    def retry_audio_generation(self, *, user, plan_id):
        return self.request_audio_generation(user=user, plan_id=plan_id, retry=True)

    def _guide_for_job(self, job):
        return GuideCard.query.filter_by(id=job.guide_id).with_for_update().first()

    def claim_audio_generation(self, job):
        guide = self._guide_for_job(job)
        if guide is None or not _same_generation(guide, job) or guide.audio_status not in {"pending", "generating"}:
            db.session.rollback()
            return AudioGenerationResult(status="stale")
        if guide.audio_status == "pending":
            guide.audio_status = "generating"
            guide.audio_error_code = None
            db.session.commit()
        return AudioGenerationResult(status="generating")

    def _mark_failed_if_current(self, job, code):
        guide = self._guide_for_job(job)
        if guide is None or not _same_generation(guide, job):
            db.session.rollback()
            return AudioGenerationResult(status="stale")
        guide.audio_status = "failed"
        guide.audio_object_key = None
        guide.audio_duration_sec = None
        guide.audio_generated_at = None
        guide.audio_error_code = code
        db.session.commit()
        return AudioGenerationResult(status="failed")

    def process_audio_generation(self, job):
        claimed = self.claim_audio_generation(job)
        if claimed.status == "stale":
            return claimed

        guide = self._guide_for_job(job)
        if guide is None or not _same_generation(guide, job) or guide.audio_status != "generating":
            db.session.rollback()
            return AudioGenerationResult(status="stale")

        try:
            synthesis = self.tts_provider.synthesize(
                text=guide.narration_text,
                language=AUDIO_LANGUAGE,
                voice=AUDIO_VOICE_PROFILE_ID,
                format=AUDIO_OUTPUT_FORMAT,
            )
            audio_bytes = _result_value(synthesis, "audio_bytes")
            content_type = _result_value(synthesis, "content_type")
            duration_sec = _result_value(synthesis, "duration_sec")
            if not isinstance(audio_bytes, bytes) or not isinstance(content_type, str) or not isinstance(duration_sec, int) or duration_sec <= 0:
                raise ValueError("Invalid TTS synthesis result")
        except Exception as error:
            return self._mark_failed_if_current(job, _controlled_error_code(error, "TTS_PROVIDER_FAILED"))

        object_key = f"guide-audio/{guide.id}/{job.source_hash}/{job.generation_token}.{AUDIO_OUTPUT_FORMAT}"
        try:
            persisted_key = self.storage.put(
                object_key=object_key,
                audio_bytes=audio_bytes,
                content_type=content_type,
            )
            if not isinstance(persisted_key, str) or not persisted_key:
                raise ValueError("Storage returned an invalid object key")
        except Exception as error:
            return self._mark_failed_if_current(job, _controlled_error_code(error, "AUDIO_STORAGE_FAILED"))

        guide = self._guide_for_job(job)
        if guide is None or not _same_generation(guide, job) or guide.audio_status != "generating":
            db.session.rollback()
            try:
                self.storage.delete(object_key=persisted_key)
            except Exception:
                pass
            return AudioGenerationResult(status="stale")

        guide.audio_status = "ready"
        guide.audio_object_key = persisted_key
        guide.audio_duration_sec = duration_sec
        guide.audio_generated_at = utc_now()
        guide.audio_error_code = None
        db.session.commit()
        return AudioGenerationResult(status="ready")


def request_audio_generation_with_job(*, user, plan_id, retry=False):
    """Atomically persist the current Guide audio intent and one durable worker job."""
    from app.services.guide_audio_jobs import AudioJobService

    service = GuideAudioService()
    phase = "owned_guide_lookup"
    guide_id = None
    sensitive_values = ()

    def set_phase(value):
        nonlocal phase
        phase = value

    def set_guide_id(value):
        nonlocal guide_id
        guide_id = value

    try:
        intent = service.request_audio_generation(
            user=user,
            plan_id=plan_id,
            retry=retry,
            commit=False,
            phase_callback=set_phase,
            guide_id_callback=set_guide_id,
        )
        guide_id = intent.guide_id
        sensitive_values = (intent.source_hash, intent.generation_token)
        job, job_created = AudioJobService().create_or_reuse(intent, phase_callback=set_phase)
        phase = "commit"
        db.session.commit()
        return intent, job, job_created
    except GuideAudioError:
        db.session.rollback()
        raise
    except SQLAlchemyError as error:
        _log_audio_database_error(
            error,
            phase=phase,
            plan_id=plan_id,
            guide_id=guide_id,
            sensitive_values=sensitive_values,
        )
        db.session.rollback()
        raise GuideAudioError("DATABASE_ERROR", "Database error", 500) from error


def serialize_audio_fields(guide, *, storage):
    status = guide.audio_status or "none"
    if status not in AUDIO_STATUSES:
        status = "failed"

    audio_url = None
    try:
        signed_url_ttl_seconds = current_app.config.get("AUDIO_SIGNED_URL_TTL_SECONDS", SIGNED_URL_TTL_SECONDS)
    except RuntimeError:
        signed_url_ttl_seconds = SIGNED_URL_TTL_SECONDS
    if status == "ready" and guide.audio_object_key and guide.audio_source_hash:
        expected_hash = None
        if guide.narration_text:
            expected_hash = build_audio_source_hash(
                narration_text=guide.narration_text,
                language=AUDIO_LANGUAGE,
                voice_profile_id=AUDIO_VOICE_PROFILE_ID,
                tts_config_version=TTS_CONFIG_VERSION,
                output_format=AUDIO_OUTPUT_FORMAT,
            )
        if expected_hash == guide.audio_source_hash:
            try:
                audio_url = storage.create_signed_url(
                    object_key=guide.audio_object_key,
                expires_in_seconds=signed_url_ttl_seconds,
                )
            except AudioStorageError:
                # Signing is a response-time convenience. A temporary storage
                # failure must not make the existing Guide text unavailable.
                audio_url = None
        else:
            status = "pending"

    return {
        "audioStatus": status,
        "audioDurationSec": guide.audio_duration_sec if status == "ready" else None,
        "audioUrl": audio_url,
    }
