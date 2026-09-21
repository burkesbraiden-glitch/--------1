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
    assert error.diagnostic_detail is None

    unsafe_detail = module.TTSProviderError("TTS_BAD_REQUEST", "bad request", diagnostic_detail="<script>body</script>")
    assert unsafe_detail.diagnostic_detail is None


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


def test_edge_submit_uses_explicit_application_user_agent_without_changing_payload_headers():
    opener = RecordingOpener()
    provider, _module = create_provider(opener)
    tts_module = require_module("app.services.tts_provider")

    provider.submit(tts_module.TTSRequest(text="讲解", language="zh-CN", voice="warm-guide-v1", format="mp3"))

    request = opener.calls[0]["request"]
    assert request.get_header("User-agent") == "Tonglvji-GuideAudio/1.0"
    assert request.get_header("User-agent") != "Mozilla/5.0"
    assert not request.get_header("User-agent").startswith("Python-urllib/")
    assert request.get_header("Content-type") == "application/json"
    assert request.get_header("Accept") == "audio/mpeg"
    assert json.loads(request.data.decode("utf-8")) == {
        "input": "讲解",
        "voice": "zh-CN-XiaoxiaoNeural",
        "speed": 1.0,
        "pitch": "0",
        "style": "general",
    }


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


def _http_error(status, body):
    return HTTPError(
        "https://edge-worker.example.test/v1/audio/speech",
        status,
        "provider error",
        {},
        io.BytesIO(body),
    )


def _submit_and_capture_http_error(error):
    provider, _module = create_provider(RecordingOpener(error=error))
    tts_module = require_module("app.services.tts_provider")

    with pytest.raises(tts_module.TTSProviderError) as captured:
        provider.submit(
            tts_module.TTSRequest(
                text="不得出现在诊断日志中的讲解全文",
                language="zh-CN",
                voice="warm-guide-v1",
                format="mp3",
            )
        )
    return captured.value


def test_edge_provider_exposes_sanitized_json_400_diagnostic_without_changing_error_semantics():
    error = _submit_and_capture_http_error(_http_error(400, b'{"error":"Invalid voice parameter"}'))

    assert error.code == "TTS_BAD_REQUEST"
    assert error.retryable is False
    assert error.diagnostic_detail == "Invalid voice parameter"


def test_edge_provider_exposes_sanitized_text_400_diagnostic_without_echoing_request_text():
    error = _submit_and_capture_http_error(
        _http_error(400, "Invalid request: 不得出现在诊断日志中的讲解全文".encode("utf-8"))
    )

    assert error.code == "TTS_BAD_REQUEST"
    assert error.retryable is False
    assert error.diagnostic_detail == "Invalid request: [redacted]"


def test_edge_provider_truncates_and_normalizes_http_error_diagnostic_detail():
    error = _submit_and_capture_http_error(_http_error(400, ("x" * 700).encode("utf-8")))

    assert error.code == "TTS_BAD_REQUEST"
    assert error.retryable is False
    assert len(error.diagnostic_detail) == 512
    assert error.diagnostic_detail == "x" * 512

    normalized = _submit_and_capture_http_error(_http_error(400, b"Invalid\r\nvoice\tparameter\x00"))
    assert normalized.diagnostic_detail == "Invalid voice parameter"


@pytest.mark.parametrize(
    "body",
    [b"<!doctype html><html><body>large page</body></html>", b"<script>large page</script>", b"\xff\x00\x81\x80"],
)
def test_edge_provider_omits_html_and_binary_http_error_bodies_from_diagnostics(body):
    error = _submit_and_capture_http_error(_http_error(400, body))

    assert error.code == "TTS_BAD_REQUEST"
    assert error.retryable is False
    assert error.diagnostic_detail is None


def test_edge_provider_redacts_credentials_and_tokens_from_http_error_diagnostic():
    diagnostic = (
        "Authorization: Bearer test-bearer Cookie=session-cookie "
        "Cloudflare-Token=cloudflare-token R2_SECRET_ACCESS_KEY=r2-secret "
        "jwt=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.signature"
    )
    error = _submit_and_capture_http_error(_http_error(400, diagnostic.encode("utf-8")))

    assert error.diagnostic_detail
    for sensitive_value in ("test-bearer", "session-cookie", "cloudflare-token", "r2-secret", "eyJhbGci"):
        assert sensitive_value not in error.diagnostic_detail
    assert "[redacted]" in error.diagnostic_detail


def test_edge_provider_keeps_controlled_error_when_http_error_body_cannot_be_read():
    error = _http_error(400, b"unreadable")

    def unreadable(*_args, **_kwargs):
        raise OSError("body unavailable")

    error.read = unreadable
    captured = _submit_and_capture_http_error(error)

    assert captured.code == "TTS_BAD_REQUEST"
    assert captured.retryable is False
    assert captured.diagnostic_detail is None


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
