import io
import json
from urllib.error import HTTPError, URLError

import pytest


def require_module(module_name):
    try:
        return __import__(module_name, fromlist=["*"])
    except ModuleNotFoundError as error:
        pytest.fail(f"P8.2B2B Edge TTS provider contract is missing: {module_name} ({error})")


class FakeHeaders:
    def __init__(self, content_type):
        self.content_type = content_type

    def get_content_type(self):
        return self.content_type


class FakeResponse:
    def __init__(self, *, body=b"mp3-bytes", content_type="audio/mpeg"):
        self.body = body
        self.headers = FakeHeaders(content_type)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.body


class RecordingOpener:
    def __init__(self, *, response=None, error=None):
        self.response = response or FakeResponse()
        self.error = error
        self.calls = []

    def __call__(self, request, *, timeout):
        self.calls.append({"request": request, "timeout": timeout})
        if self.error is not None:
            raise self.error
        return self.response


def create_provider(opener, **overrides):
    module = require_module("app.services.tts.edge_tts_provider")
    config = module.EdgeTTSConfig(
        base_url=overrides.get("base_url", "https://edge-worker.example.test/"),
        voice=overrides.get("voice", "zh-CN-XiaoxiaoNeural"),
        speed=overrides.get("speed", 1.0),
        pitch=overrides.get("pitch", "0"),
        style=overrides.get("style", "general"),
        timeout_seconds=overrides.get("timeout_seconds", 9),
    )
    return module.EdgeTTSProvider(config=config, opener=opener), module


def test_provider_neutral_contract_keeps_submit_poll_fetch_and_synthesize():
    module = require_module("app.services.tts_provider")

    for method_name in ("submit", "poll", "fetch", "synthesize"):
        assert hasattr(module.TTSProvider, method_name)
    error = module.TTSProviderError("TTS_TIMEOUT", "timeout", retryable=True)
    assert error.code == "TTS_TIMEOUT"
    assert error.retryable is True


def test_edge_submit_posts_configured_worker_payload_and_returns_direct_ready_mp3():
    opener = RecordingOpener(response=FakeResponse(body=b"edge-mp3"))
    provider, _module = create_provider(opener, speed=1.25, pitch="6", style="gentle", timeout_seconds=17)
    tts_module = require_module("app.services.tts_provider")

    result = provider.submit(
        tts_module.TTSRequest(
            text="我们现在来到故宫博物院，一起看看屋顶。",
            language="zh-CN",
            voice="warm-guide-v1",
            format="mp3",
        )
    )

    assert result.status == "ready"
    assert result.provider_job_id is None
    assert result.audio_bytes == b"edge-mp3"
    assert result.content_type == "audio/mpeg"
    assert len(opener.calls) == 1
    call = opener.calls[0]
    assert call["request"].full_url == "https://edge-worker.example.test/v1/audio/speech"
    assert call["timeout"] == 17
    assert call["request"].get_header("Content-type") == "application/json"
    assert json.loads(call["request"].data.decode("utf-8")) == {
        "input": "我们现在来到故宫博物院，一起看看屋顶。",
        "voice": "zh-CN-XiaoxiaoNeural",
        "speed": 1.25,
        "pitch": "6",
        "style": "gentle",
    }


def test_edge_submit_uses_configured_voice_instead_of_business_profile_id():
    opener = RecordingOpener()
    provider, _module = create_provider(opener, voice="zh-CN-XiaoyiNeural")
    tts_module = require_module("app.services.tts_provider")

    provider.submit(tts_module.TTSRequest(text="讲解", language="zh-CN", voice="warm-guide-v1", format="mp3"))

    payload = json.loads(opener.calls[0]["request"].data.decode("utf-8"))
    assert payload["voice"] == "zh-CN-XiaoyiNeural"


@pytest.mark.parametrize(
    ("error", "expected_code", "retryable"),
    [
        (
            HTTPError("https://edge-worker.example.test/v1/audio/speech", 429, "rate limited", {}, io.BytesIO(b"rate")),
            "TTS_RATE_LIMITED",
            True,
        ),
        (
            HTTPError("https://edge-worker.example.test/v1/audio/speech", 503, "unavailable", {}, io.BytesIO(b"server")),
            "TTS_PROVIDER_UNAVAILABLE",
            True,
        ),
        (
            HTTPError("https://edge-worker.example.test/v1/audio/speech", 400, "bad request", {}, io.BytesIO(b"bad")),
            "TTS_BAD_REQUEST",
            False,
        ),
        (TimeoutError("timeout"), "TTS_TIMEOUT", True),
        (URLError("network down"), "TTS_NETWORK", True),
    ],
)
def test_edge_provider_maps_transport_errors_to_controlled_retryable_domain_errors(error, expected_code, retryable):
    provider, _module = create_provider(RecordingOpener(error=error))
    tts_module = require_module("app.services.tts_provider")

    with pytest.raises(tts_module.TTSProviderError) as captured:
        provider.submit(tts_module.TTSRequest(text="讲解", language="zh-CN", voice="warm-guide-v1", format="mp3"))

    assert captured.value.code == expected_code
    assert captured.value.retryable is retryable


@pytest.mark.parametrize("content_type", ["text/html", "application/json", "text/plain"])
def test_edge_provider_rejects_non_mp3_response(content_type):
    provider, _module = create_provider(RecordingOpener(response=FakeResponse(content_type=content_type)))
    tts_module = require_module("app.services.tts_provider")

    with pytest.raises(tts_module.TTSProviderError) as captured:
        provider.submit(tts_module.TTSRequest(text="讲解", language="zh-CN", voice="warm-guide-v1", format="mp3"))

    assert captured.value.code == "TTS_PROVIDER_CONTENT_TYPE_INVALID"
    assert captured.value.retryable is False


def test_edge_provider_rejects_empty_mp3_response():
    provider, _module = create_provider(RecordingOpener(response=FakeResponse(body=b"")))
    tts_module = require_module("app.services.tts_provider")

    with pytest.raises(tts_module.TTSProviderError) as captured:
        provider.submit(tts_module.TTSRequest(text="讲解", language="zh-CN", voice="warm-guide-v1", format="mp3"))

    assert captured.value.code == "TTS_PROVIDER_RESULT_INVALID"
    assert captured.value.retryable is False


def test_edge_provider_sanitizes_response_body_and_sensitive_headers_from_errors():
    secret = "edge-test-secret"
    error = HTTPError(
        "https://edge-worker.example.test/v1/audio/speech",
        500,
        f"Authorization: Bearer {secret}",
        {"X-Internal-Token": secret},
        io.BytesIO(f"internal body {secret}".encode("utf-8")),
    )
    provider, _module = create_provider(RecordingOpener(error=error))
    tts_module = require_module("app.services.tts_provider")

    with pytest.raises(tts_module.TTSProviderError) as captured:
        provider.submit(tts_module.TTSRequest(text="讲解", language="zh-CN", voice="warm-guide-v1", format="mp3"))

    assert secret not in str(captured.value)
    assert "Authorization" not in str(captured.value)
    assert "internal body" not in str(captured.value)


def test_edge_provider_keeps_poll_and_fetch_as_controlled_non_async_errors():
    provider, _module = create_provider(RecordingOpener())
    tts_module = require_module("app.services.tts_provider")

    for operation in (provider.poll, provider.fetch):
        with pytest.raises(tts_module.TTSProviderError) as captured:
            operation("other-provider-job-1")
        assert captured.value.code == "TTS_PROVIDER_ASYNC_UNSUPPORTED"
        assert captured.value.retryable is False


def test_edge_provider_does_not_hardcode_the_public_demo_address():
    module = require_module("app.services.tts.edge_tts_provider")
    source = open(module.__file__, encoding="utf-8").read()

    assert "tts.wangwangit.com" not in source
