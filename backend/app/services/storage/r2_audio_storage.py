from dataclasses import dataclass

from app.services.audio_storage import AudioStorageError


def _required_value(value):
    return value.strip() if isinstance(value, str) else ""


@dataclass(frozen=True)
class R2StorageConfig:
    account_id: str
    access_key_id: str
    secret_access_key: str
    bucket: str

    @property
    def endpoint_url(self):
        return f"https://{self.account_id}.r2.cloudflarestorage.com"


def _map_client_error(error):
    if isinstance(error, AudioStorageError):
        return error

    message = str(error).casefold()
    response = getattr(error, "response", None)
    response_error = response.get("Error", {}) if isinstance(response, dict) else {}
    response_code = str(response_error.get("Code", "")).casefold()
    status_code = response.get("ResponseMetadata", {}).get("HTTPStatusCode") if isinstance(response, dict) else None
    if isinstance(error, FileNotFoundError) or response_code in {"nosuchkey", "notfound"} or status_code == 404:
        return AudioStorageError("AUDIO_STORAGE_NOT_FOUND", "R2 object was not found", retryable=False)
    if isinstance(error, PermissionError) or response_code in {"accessdenied", "invalidaccesskeyid"} or status_code in {401, 403}:
        return AudioStorageError("AUDIO_STORAGE_ACCESS_DENIED", "R2 access was denied", retryable=False)
    if isinstance(error, TimeoutError) or "timeout" in message or "timed out" in message:
        return AudioStorageError("AUDIO_STORAGE_TIMEOUT", "R2 request timed out", retryable=True)
    if isinstance(error, (ConnectionError, OSError)) or "connection" in message or "network" in message:
        return AudioStorageError("AUDIO_STORAGE_NETWORK", "R2 network request failed", retryable=True)
    if status_code == 429 or (isinstance(status_code, int) and 500 <= status_code <= 599) or "rate limit" in message:
        return AudioStorageError("AUDIO_STORAGE_UNAVAILABLE", "R2 is temporarily unavailable", retryable=True)
    return AudioStorageError("AUDIO_STORAGE_ERROR", "R2 request failed", retryable=False)


class _R2S3Client:
    def __init__(self, *, config):
        try:
            import boto3
            from botocore.client import Config
        except ImportError as error:
            raise AudioStorageError(
                "AUDIO_STORAGE_DEPENDENCY_MISSING",
                "boto3 is not installed",
                retryable=False,
            ) from error

        self._client = boto3.client(
            "s3",
            endpoint_url=config.endpoint_url,
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )

    def put_object(self, **kwargs):
        return self._client.put_object(**kwargs)

    def delete_object(self, **kwargs):
        return self._client.delete_object(**kwargs)

    def generate_presigned_url(self, operation_name, *, Params, ExpiresIn):
        return self._client.generate_presigned_url(operation_name, Params=Params, ExpiresIn=ExpiresIn)


class R2AudioStorage:
    def __init__(self, *, config, client=None):
        self.config = config
        self.account_id = _required_value(config.account_id)
        self.access_key_id = _required_value(config.access_key_id)
        self.secret_access_key = _required_value(config.secret_access_key)
        self.bucket = _required_value(config.bucket)
        if not all((self.account_id, self.access_key_id, self.secret_access_key, self.bucket)):
            raise AudioStorageError(
                "AUDIO_STORAGE_CONFIG_INVALID",
                "R2 configuration is incomplete",
                retryable=False,
            )
        self.endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"
        self.region_name = "auto"
        self._client = client or _R2S3Client(config=config)

    def put(self, *, object_key, audio_bytes, content_type):
        if content_type != "audio/mpeg":
            raise AudioStorageError(
                "AUDIO_STORAGE_CONTENT_TYPE_INVALID",
                "Guide audio must use audio/mpeg",
                retryable=False,
            )
        try:
            self._client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=audio_bytes,
                ContentType="audio/mpeg",
            )
        except Exception as error:
            raise _map_client_error(error) from error
        return object_key

    def delete(self, *, object_key):
        try:
            self._client.delete_object(Bucket=self.bucket, Key=object_key)
        except Exception as error:
            raise _map_client_error(error) from error

    def create_signed_url(self, *, object_key, expires_in_seconds):
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": object_key},
                ExpiresIn=expires_in_seconds,
            )
        except Exception as error:
            raise _map_client_error(error) from error
        if not isinstance(url, str) or not url:
            raise AudioStorageError("AUDIO_STORAGE_RESULT_INVALID", "R2 returned an invalid signed URL", retryable=False)
        return url
