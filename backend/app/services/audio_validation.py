from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from mutagen.mp3 import MP3


MAX_AUDIO_BYTES = 8 * 1024 * 1024
MAX_AUDIO_DURATION_SECONDS = 240


class AudioValidationError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ValidatedAudio:
    audio_bytes: bytes
    content_type: str
    duration_sec: int


def normalize_duration_seconds(raw_duration_seconds):
    try:
        value = Decimal(str(raw_duration_seconds))
    except Exception as error:
        raise AudioValidationError("AUDIO_DURATION_INVALID", "Audio duration is invalid") from error

    if not value.is_finite() or value <= 0:
        raise AudioValidationError("AUDIO_DURATION_INVALID", "Audio duration is invalid")

    rounded = int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return max(1, rounded)


def _looks_like_mp3(audio_bytes):
    return audio_bytes.startswith(b"ID3") or (
        len(audio_bytes) >= 2 and audio_bytes[0] == 0xFF and (audio_bytes[1] & 0xE0) == 0xE0
    )


def extract_mp3_duration_seconds(audio_bytes):
    try:
        info = MP3(BytesIO(audio_bytes)).info
        return normalize_duration_seconds(info.length)
    except AudioValidationError:
        raise
    except Exception as error:
        raise AudioValidationError("AUDIO_INVALID_MP3", "Audio bytes are not a valid MP3") from error


def validate_generated_audio(audio_bytes):
    if not isinstance(audio_bytes, bytes) or not audio_bytes:
        raise AudioValidationError("AUDIO_EMPTY", "Generated audio is empty")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise AudioValidationError("AUDIO_SIZE_EXCEEDED", "Generated audio exceeds the size limit")
    if not _looks_like_mp3(audio_bytes):
        raise AudioValidationError("AUDIO_INVALID_MP3", "Generated audio is not an MP3")

    duration_sec = extract_mp3_duration_seconds(audio_bytes)
    if duration_sec <= 0 or duration_sec > MAX_AUDIO_DURATION_SECONDS:
        raise AudioValidationError("AUDIO_DURATION_INVALID", "Generated audio duration is invalid")

    return ValidatedAudio(
        audio_bytes=audio_bytes,
        content_type="audio/mpeg",
        duration_sec=duration_sec,
    )
