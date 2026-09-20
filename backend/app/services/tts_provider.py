from dataclasses import dataclass
from typing import Protocol


class TTSProviderError(Exception):
    def __init__(self, code, message, *, retryable=False, retry_after_seconds=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds


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
