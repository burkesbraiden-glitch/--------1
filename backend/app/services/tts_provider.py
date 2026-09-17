from dataclasses import dataclass
from typing import Protocol


class TTSProviderError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class SynthesisResult:
    audio_bytes: bytes
    content_type: str
    duration_sec: int


class TTSProvider(Protocol):
    def synthesize(self, *, text, language, voice, format):
        """Return SynthesisResult-compatible audio data without persisting it."""


class UnconfiguredTTSProvider:
    def synthesize(self, *, text, language, voice, format):
        raise TTSProviderError(
            "TTS_PROVIDER_NOT_CONFIGURED",
            "TTS provider is not configured",
        )
