from dataclasses import dataclass
import re
from typing import Protocol


_DIAGNOSTIC_DETAIL_MAX_CHARS = 512
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f-\x9f]+")
_BEARER_TOKEN = re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]+")
_SENSITIVE_ASSIGNMENT = re.compile(
    r"""(?ix)
    \b(?:
        authorization|cookie|set-cookie|cloudflare(?:[-_ ]?(?:token|api[-_ ]?(?:token|key)))?|
        r2(?:[-_ ]?(?:access[-_ ]?key(?:[-_ ]?id)?|secret[-_ ]?access[-_ ]?key))?|
        jwt|token|api[-_ ]?key|access[-_ ]?key(?:[-_ ]?id)?|secret(?:[-_ ]?access[-_ ]?key)?
    )\b\s*(?::|=)\s*(?:bearer\s+)?(?:"[^"]*"|'[^']*'|[^\s,;]+)
    """
)
_JWT = re.compile(r"\beyJ[a-zA-Z0-9_-]{5,}\.[a-zA-Z0-9_-]{5,}\.[a-zA-Z0-9_-]{3,}\b")
_URL = re.compile(r"https?://[^\s'\"]+")


def sanitize_tts_diagnostic_detail(value, *, sensitive_values=()):
    """Return a short, log-only Provider detail with common credentials removed."""
    if not isinstance(value, str):
        return None

    detail = value
    for sensitive_value in sensitive_values:
        if isinstance(sensitive_value, str) and sensitive_value:
            detail = detail.replace(sensitive_value, "[redacted]")
    detail = _CONTROL_CHARACTERS.sub(" ", detail)
    detail = " ".join(detail.split())
    if not detail or detail.startswith("<"):
        return None
    detail = _BEARER_TOKEN.sub("Bearer [redacted]", detail)
    detail = _SENSITIVE_ASSIGNMENT.sub("[redacted]", detail)
    detail = _JWT.sub("[redacted]", detail)
    detail = _URL.sub("[redacted]", detail)
    return detail[:_DIAGNOSTIC_DETAIL_MAX_CHARS] or None


class TTSProviderError(Exception):
    def __init__(
        self,
        code,
        message,
        *,
        retryable=False,
        retry_after_seconds=None,
        diagnostic_detail=None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds
        self.diagnostic_detail = sanitize_tts_diagnostic_detail(diagnostic_detail)


@dataclass(frozen=True)
class SynthesisResult:
    audio_bytes: bytes
    content_type: str
    duration_sec: int


@dataclass(frozen=True)
class TTSRequest:
    text: str
    language: str
    voice: str
    format: str


@dataclass(frozen=True)
class TTSJobResult:
    status: str
    provider_job_id: str | None = None
    audio_bytes: bytes | None = None
    content_type: str | None = None
    retry_after_seconds: int | None = None


class TTSProvider(Protocol):
    def submit(self, request: TTSRequest) -> TTSJobResult:
        """Start synthesis or return an immediately-ready result."""

    def poll(self, provider_job_id: str) -> TTSJobResult:
        """Read an existing provider job without creating a new one."""

    def fetch(self, provider_job_id: str) -> SynthesisResult:
        """Fetch completed provider audio through an opaque provider job ID."""

    def synthesize(self, *, text, language, voice, format):
        """Return SynthesisResult-compatible audio data without persisting it."""


class UnconfiguredTTSProvider:
    def _raise(self):
        raise TTSProviderError(
            "TTS_PROVIDER_NOT_CONFIGURED",
            "TTS provider is not configured",
            retryable=False,
        )

    def submit(self, request):
        self._raise()

    def poll(self, provider_job_id):
        self._raise()

    def fetch(self, provider_job_id):
        self._raise()

    def synthesize(self, *, text, language, voice, format):
        self._raise()


def create_tts_provider(config):
    """Build the configured provider without coupling callers to a vendor module."""
    from app.services.tts.factory import create_tts_provider as create

    return create(config)
