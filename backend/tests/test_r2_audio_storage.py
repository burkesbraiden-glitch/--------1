import pytest


def require_module(module_name):
    try:
        return __import__(module_name, fromlist=["*"])
    except ModuleNotFoundError as error:
        pytest.fail(f"P8.2B2B R2 storage contract is missing: {module_name} ({error})")


class FakeR2Client:
    def __init__(self, *, error=None):
        self.error = error
        self.put_calls = []
        self.delete_calls = []
        self.sign_calls = []

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return {"ETag": "etag-v1"}

    def delete_object(self, **kwargs):
        self.delete_calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return {}

    def generate_presigned_url(self, operation_name, *, Params, ExpiresIn):
        self.sign_calls.append({"operation_name": operation_name, "Params": Params, "ExpiresIn": ExpiresIn})
        if self.error is not None:
            raise self.error
        return "https://account.r2.cloudflarestorage.com/private-guide.mp3?X-Amz-Signature=test"


def storage_with_client(client, **overrides):
    module = require_module("app.services.storage.r2_audio_storage")
    config = module.R2StorageConfig(
        account_id=overrides.get("account_id", "account-id-123"),
        access_key_id=overrides.get("access_key_id", "r2-access-key"),
        secret_access_key=overrides.get("secret_access_key", "r2-secret-key"),
        bucket=overrides.get("bucket", "tonglvji-private-audio"),
    )
    return module.R2AudioStorage(config=config, client=client), module


def test_audio_storage_error_has_controlled_code_and_retryability():
    module = require_module("app.services.audio_storage")
    error = module.AudioStorageError("AUDIO_STORAGE_TIMEOUT", "timeout", retryable=True)

    assert error.code == "AUDIO_STORAGE_TIMEOUT"
    assert error.retryable is True


def test_r2_put_delete_and_sign_keep_private_server_generated_object_key_without_network():
    client = FakeR2Client()
    storage, _module = storage_with_client(client)
    key = f"guide-audio/500/{'a' * 64}/token-v1.mp3"

    persisted_key = storage.put(object_key=key, audio_bytes=b"mp3-bytes", content_type="audio/mpeg")
    signed_url = storage.create_signed_url(object_key=key, expires_in_seconds=300)
    storage.delete(object_key=key)

    assert storage.endpoint_url == "https://account-id-123.r2.cloudflarestorage.com"
    assert storage.region_name == "auto"
    assert persisted_key == key
    assert client.put_calls == [
        {
            "Bucket": "tonglvji-private-audio",
            "Key": key,
            "Body": b"mp3-bytes",
            "ContentType": "audio/mpeg",
        }
    ]
    assert "ACL" not in client.put_calls[0]
    assert signed_url.startswith("https://account.r2.cloudflarestorage.com/")
    assert client.sign_calls == [
        {
            "operation_name": "get_object",
            "Params": {"Bucket": "tonglvji-private-audio", "Key": key},
            "ExpiresIn": 300,
        }
    ]
    assert client.delete_calls == [{"Bucket": "tonglvji-private-audio", "Key": key}]


def test_r2_adapter_rejects_non_mp3_content_type_without_client_call():
    client = FakeR2Client()
    storage, _module = storage_with_client(client)
    audio_module = require_module("app.services.audio_storage")

    with pytest.raises(audio_module.AudioStorageError) as captured:
        storage.put(object_key="guide-audio/500/test.mp3", audio_bytes=b"bytes", content_type="text/plain")

    assert captured.value.code == "AUDIO_STORAGE_CONTENT_TYPE_INVALID"
    assert captured.value.retryable is False
    assert client.put_calls == []


@pytest.mark.parametrize(
    ("operation", "client_error", "expected_code", "retryable"),
    [
        ("put", TimeoutError("timeout"), "AUDIO_STORAGE_TIMEOUT", True),
        ("put", ConnectionError("network"), "AUDIO_STORAGE_NETWORK", True),
        ("delete", FileNotFoundError("missing"), "AUDIO_STORAGE_NOT_FOUND", False),
        ("sign", PermissionError("access denied"), "AUDIO_STORAGE_ACCESS_DENIED", False),
    ],
)
def test_r2_maps_client_failures_to_controlled_storage_errors(operation, client_error, expected_code, retryable):
    storage, _module = storage_with_client(FakeR2Client(error=client_error))
    audio_module = require_module("app.services.audio_storage")
    key = f"guide-audio/500/{'a' * 64}/token-v1.mp3"

    with pytest.raises(audio_module.AudioStorageError) as captured:
        if operation == "put":
            storage.put(object_key=key, audio_bytes=b"mp3-bytes", content_type="audio/mpeg")
        elif operation == "delete":
            storage.delete(object_key=key)
        else:
            storage.create_signed_url(object_key=key, expires_in_seconds=300)

    assert captured.value.code == expected_code
    assert captured.value.retryable is retryable


def test_r2_adapter_rejects_missing_configuration_without_creating_client():
    module = require_module("app.services.storage.r2_audio_storage")
    audio_module = require_module("app.services.audio_storage")
    client = FakeR2Client()

    with pytest.raises(audio_module.AudioStorageError) as captured:
        module.R2AudioStorage(
            config=module.R2StorageConfig(account_id="", access_key_id="", secret_access_key="", bucket=""),
            client=client,
        )

    assert captured.value.code == "AUDIO_STORAGE_CONFIG_INVALID"
    assert captured.value.retryable is False
    assert client.put_calls == []


def test_r2_storage_error_sanitizes_access_key_secret_and_presigned_url():
    access_key = "r2-access-key"
    secret = "r2-secret-key"
    signed_url = "https://account.r2.cloudflarestorage.com/object?X-Amz-Signature=secret-signature"
    storage, _module = storage_with_client(
        FakeR2Client(error=RuntimeError(f"{access_key} {secret} {signed_url}")),
        access_key_id=access_key,
        secret_access_key=secret,
    )
    audio_module = require_module("app.services.audio_storage")

    with pytest.raises(audio_module.AudioStorageError) as captured:
        storage.create_signed_url(object_key="guide-audio/500/test.mp3", expires_in_seconds=300)

    assert access_key not in str(captured.value)
    assert secret not in str(captured.value)
    assert "X-Amz-Signature" not in str(captured.value)
