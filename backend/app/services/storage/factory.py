from app.services.audio_storage import AudioStorageError, UnconfiguredAudioStorage
from app.services.storage.r2_audio_storage import R2AudioStorage, R2StorageConfig


def _provider_name(config):
    value = config.get("AUDIO_STORAGE_PROVIDER", "unconfigured")
    return value.strip().casefold() if isinstance(value, str) else "unconfigured"


def create_audio_storage(config):
    provider_name = _provider_name(config)
    if provider_name == "r2":
        return R2AudioStorage(
            config=R2StorageConfig(
                account_id=config.get("R2_ACCOUNT_ID", ""),
                access_key_id=config.get("R2_ACCESS_KEY_ID", ""),
                secret_access_key=config.get("R2_SECRET_ACCESS_KEY", ""),
                bucket=config.get("R2_BUCKET", ""),
            )
        )
    if provider_name in {"fake", "unconfigured", ""}:
        # Tests inject storage directly; no local fake object store is created.
        return UnconfiguredAudioStorage()
    raise AudioStorageError("AUDIO_STORAGE_CONFIG_INVALID", "Unsupported audio storage provider", retryable=False)
