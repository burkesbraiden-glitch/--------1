import importlib

import pytest


def require_validation_module():
    try:
        return importlib.import_module("app.services.audio_validation")
    except ModuleNotFoundError as error:
        pytest.fail(f"P8.2B2 audio validation contract is missing: {error}")


def minimal_valid_mp3_bytes(frame_count=40):
    """MPEG-1 Layer III frame headers plus zeroed frame payloads; no speech content."""
    frame = b"\xff\xfb\x90\x00" + (b"\x00" * 413)
    return frame * frame_count


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"<html><body>provider error</body></html>",
        b'{"error":"provider error"}',
        b"not an mp3",
    ],
)
def test_generated_audio_rejects_empty_and_non_mp3_bytes(payload):
    module = require_validation_module()

    with pytest.raises(module.AudioValidationError):
        module.validate_generated_audio(payload)


def test_generated_audio_accepts_a_real_mp3_container_and_returns_server_duration():
    module = require_validation_module()

    result = module.validate_generated_audio(minimal_valid_mp3_bytes())

    assert result.content_type == "audio/mpeg"
    assert result.duration_sec == 1
    assert result.audio_bytes == minimal_valid_mp3_bytes()


def test_generated_audio_rejects_over_eight_mebibytes_before_storage():
    module = require_validation_module()
    too_large_mp3 = minimal_valid_mp3_bytes((8 * 1024 * 1024 // 417) + 1)

    with pytest.raises(module.AudioValidationError, match="SIZE|size"):
        module.validate_generated_audio(too_large_mp3)


def test_generated_audio_rejects_non_positive_or_overlong_server_duration(monkeypatch):
    module = require_validation_module()
    payload = minimal_valid_mp3_bytes()

    monkeypatch.setattr(module, "extract_mp3_duration_seconds", lambda _audio_bytes: 0)
    with pytest.raises(module.AudioValidationError, match="DURATION|duration"):
        module.validate_generated_audio(payload)

    monkeypatch.setattr(module, "extract_mp3_duration_seconds", lambda _audio_bytes: 241)
    with pytest.raises(module.AudioValidationError, match="DURATION|duration"):
        module.validate_generated_audio(payload)


def test_duration_rounding_is_half_up_to_nearest_second_with_one_second_minimum():
    module = require_validation_module()

    assert module.normalize_duration_seconds(0.01) == 1
    assert module.normalize_duration_seconds(0.5) == 1
    assert module.normalize_duration_seconds(1.49) == 1
    assert module.normalize_duration_seconds(1.5) == 2
    assert module.normalize_duration_seconds(2.5) == 3
