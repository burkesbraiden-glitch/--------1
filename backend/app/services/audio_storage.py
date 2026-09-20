from typing import Protocol


class AudioStorageError(Exception):
    def __init__(self, code, message, *, retryable=False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class AudioStorage(Protocol):
    def put(self, *, object_key, audio_bytes, content_type):
        """Persist audio bytes and return the opaque object key."""

    def delete(self, *, object_key):
        """Best-effort deletion for stale generated objects."""

    def create_signed_url(self, *, object_key, expires_in_seconds):
        """Return a short-lived URL without persisting it."""


class UnconfiguredAudioStorage:
    def _raise(self):
        raise AudioStorageError(
            "AUDIO_STORAGE_NOT_CONFIGURED",
            "Audio storage is not configured",
        )

    def put(self, *, object_key, audio_bytes, content_type):
        self._raise()

    def delete(self, *, object_key):
        self._raise()

    def create_signed_url(self, *, object_key, expires_in_seconds):
        self._raise()


def create_audio_storage(config):
    """Build the configured private audio storage without exposing a vendor API."""
    from app.services.storage.factory import create_audio_storage as create

    return create(config)
