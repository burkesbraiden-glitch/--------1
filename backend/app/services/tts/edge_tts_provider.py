from dataclasses import dataclass
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from app.services.tts_provider import (
    SynthesisResult,
    TTSJobResult,
    TTSProviderError,
    TTSRequest,
    sanitize_tts_diagnostic_detail,
)


_HTTP_ERROR_BODY_READ_LIMIT = 4096
EDGE_TTS_USER_AGENT = "Tonglvji-GuideAudio/1.0"


def _required_value(value):
    return value.strip() if isinstance(value, str) else ""


@dataclass(frozen=True)
class EdgeTTSConfig:
    base_url: str
    voice: str
    speed: float = 1.0
    pitch: str = "0"
    style: str = "general"
    timeout_seconds: int = 30


def _map_transport_error(error, *, sensitive_values=()):
    if isinstance(error, TTSProviderError):
        return error
    if isinstance(error, HTTPError):
        diagnostic_detail = _http_error_diagnostic_detail(error, sensitive_values=sensitive_values)
        if error.code == 429:
            return TTSProviderError(
                "TTS_RATE_LIMITED",
                "Edge TTS rate limit reached",
                retryable=True,
                diagnostic_detail=diagnostic_detail,
            )
        if 500 <= error.code <= 599:
            return TTSProviderError(
                "TTS_PROVIDER_UNAVAILABLE",
                "Edge TTS is temporarily unavailable",
                retryable=True,
                diagnostic_detail=diagnostic_detail,
            )
        return TTSProviderError(
            "TTS_BAD_REQUEST",
            "Edge TTS rejected the request",
            retryable=False,
            diagnostic_detail=diagnostic_detail,
        )
    if isinstance(error, TimeoutError):
        return TTSProviderError("TTS_TIMEOUT", "Edge TTS request timed out", retryable=True)
    if isinstance(error, (ConnectionError, URLError)):
        return TTSProviderError("TTS_NETWORK", "Edge TTS network request failed", retryable=True)
    return TTSProviderError("TTS_PROVIDER_ERROR", "Edge TTS request failed", retryable=False)


class EdgeTTSProvider:
    def __init__(self, *, config, opener=None):
        self.config = config
        self._base_url = _required_value(config.base_url).rstrip("/")
        self._voice = _required_value(config.voice)
        self._pitch = str(config.pitch).strip()
        self._style = _required_value(config.style)
        try:
            self._speed = float(config.speed)
            self._timeout_seconds = int(config.timeout_seconds)
        except (TypeError, ValueError) as error:
            raise TTSProviderError(
                "TTS_PROVIDER_CONFIG_INVALID",
                "Edge TTS configuration is invalid",
                retryable=False,
            ) from error

        parsed = urlsplit(self._base_url)
        if (
            not self._base_url
            or parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or not self._voice
            or not self._pitch
            or not self._style
            or self._speed <= 0
            or self._timeout_seconds <= 0
        ):
            raise TTSProviderError(
                "TTS_PROVIDER_CONFIG_INVALID",
                "Edge TTS configuration is incomplete",
                retryable=False,
            )
        self._endpoint_url = f"{self._base_url}/v1/audio/speech"
        self._opener = opener or urlopen

    def submit(self, request):
        audio_bytes, content_type = self._request_audio(request)
        return TTSJobResult(status="ready", audio_bytes=audio_bytes, content_type=content_type)

    def poll(self, provider_job_id):
        self._raise_async_unsupported()

    def fetch(self, provider_job_id):
        self._raise_async_unsupported()

    def synthesize(self, *, text, language, voice, format):
        audio_bytes, content_type = self._request_audio(
            TTSRequest(text=text, language=language, voice=voice, format=format)
        )
        return SynthesisResult(audio_bytes=audio_bytes, content_type=content_type, duration_sec=0)

    def _request_audio(self, request):
        if not isinstance(request, TTSRequest) or not _required_value(request.text):
            raise TTSProviderError("TTS_BAD_REQUEST", "Edge TTS request is invalid", retryable=False)

        body = json.dumps(
            {
                "input": request.text,
                "voice": self._voice,
                "speed": self._speed,
                "pitch": self._pitch,
                "style": self._style,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        http_request = Request(
            self._endpoint_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
                "User-Agent": EDGE_TTS_USER_AGENT,
            },
            method="POST",
        )
        try:
            with self._opener(http_request, timeout=self._timeout_seconds) as response:
                content_type = _response_content_type(response)
                audio_bytes = response.read()
        except Exception as error:
            raise _map_transport_error(error, sensitive_values=(request.text,)) from error

        if content_type != "audio/mpeg":
            raise TTSProviderError(
                "TTS_PROVIDER_CONTENT_TYPE_INVALID",
                "Edge TTS returned an unexpected content type",
                retryable=False,
            )
        if not isinstance(audio_bytes, bytes) or not audio_bytes:
            raise TTSProviderError("TTS_PROVIDER_RESULT_INVALID", "Edge TTS returned empty audio", retryable=False)
        return audio_bytes, content_type

    @staticmethod
    def _raise_async_unsupported():
        raise TTSProviderError(
            "TTS_PROVIDER_ASYNC_UNSUPPORTED",
            "Edge TTS does not support provider job polling",
            retryable=False,
        )


def _response_content_type(response):
    headers = getattr(response, "headers", None)
    get_content_type = getattr(headers, "get_content_type", None)
    if callable(get_content_type):
        value = get_content_type()
    elif hasattr(headers, "get"):
        value = headers.get("Content-Type", "")
    else:
        value = ""
    return str(value).split(";", 1)[0].strip().casefold()


def _http_error_diagnostic_detail(error, *, sensitive_values):
    try:
        body = error.read(_HTTP_ERROR_BODY_READ_LIMIT)
    except Exception:
        return None
    if not isinstance(body, bytes) or not body:
        return None
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return None

    candidate = _diagnostic_text_from_response_body(text)
    return sanitize_tts_diagnostic_detail(candidate, sensitive_values=sensitive_values)


def _diagnostic_text_from_response_body(text):
    candidate = text.strip()
    if not candidate or _looks_like_html(candidate):
        return None
    if candidate.startswith(("{", "[")):
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        return _json_diagnostic_text(payload)
    return candidate


def _json_diagnostic_text(payload):
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict):
        return None
    for key in ("message", "error_description", "error", "detail"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            nested = _json_diagnostic_text(value)
            if nested:
                return nested
    return None


def _looks_like_html(value):
    return value.startswith("<")
