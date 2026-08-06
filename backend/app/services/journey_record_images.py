from copy import deepcopy
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
from uuid import uuid4

from app.services.journey_record_snapshots import (
    JourneyRecordSnapshotValidationError,
    validate_journey_record_snapshot,
)


_IMAGE_TYPES = (
    (b"\x89PNG\r\n\x1a\n", ".png", "image/png"),
    (b"\xff\xd8\xff", ".jpg", "image/jpeg"),
)


class JourneyRecordImageError(Exception):
    def __init__(self, code, message, status_code, details=None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


@dataclass
class PreparedRecordImageCopies:
    record_id: int
    operation_id: str
    staging_directory: Path | None
    final_directory: Path
    assets_by_submission_id: dict[int, dict]
    staged_files: tuple[Path, ...]
    published: bool = False
    storage_root: Path | None = None


def _error_source_missing():
    raise JourneyRecordImageError(
        "JOURNEY_RECORD_SOURCE_IMAGE_MISSING",
        "Journey record source image is unavailable",
        409,
    )


def _error_copy_failed():
    raise JourneyRecordImageError("RECORD_IMAGE_COPY_FAILED", "Record image copy failed", 500)


def _error_not_found():
    raise JourneyRecordImageError("JOURNEY_RECORD_IMAGE_NOT_FOUND", "Journey record image not found", 404)


def _detect_image_type(data):
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return ".webp", "image/webp"
    for signature, extension, content_type in _IMAGE_TYPES:
        if data.startswith(signature):
            return extension, content_type
    _error_source_missing()


def _require_record_id(record_id):
    if not isinstance(record_id, int) or isinstance(record_id, bool) or record_id < 1:
        _error_copy_failed()


def _task_source_path(task_image_root, storage_key):
    if not isinstance(storage_key, str) or not storage_key.startswith("task-images/") or "\\" in storage_key:
        _error_source_missing()
    filename = storage_key.removeprefix("task-images/")
    if not filename or "/" in filename or filename in {".", ".."} or Path(filename).is_absolute():
        _error_source_missing()
    root = Path(task_image_root).resolve()
    source = root / filename
    try:
        source.resolve().relative_to(root)
    except ValueError:
        _error_source_missing()
    if source.is_symlink() or not source.is_file():
        _error_source_missing()
    return source


def _record_asset_path(record_image_root, record_id, storage_key):
    prefix = f"record-images/{record_id}/"
    if not isinstance(storage_key, str) or not storage_key.startswith(prefix) or "\\" in storage_key:
        _error_not_found()
    filename = storage_key.removeprefix(prefix)
    if not filename or "/" in filename or filename in {".", ".."} or Path(filename).is_absolute():
        _error_not_found()
    root = Path(record_image_root).resolve()
    candidate = root / str(record_id) / filename
    try:
        candidate.resolve().relative_to(root)
    except ValueError:
        _error_not_found()
    if candidate.is_symlink() or not candidate.is_file():
        _error_not_found()
    return candidate


def _is_link(path):
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def _remove_owned_directory(directory, expected_parent, trusted_root):
    if directory is None or not directory.exists() and not directory.is_symlink():
        return
    expected_parent = Path(expected_parent)
    if directory.parent != expected_parent or _is_link(expected_parent) or _is_link(directory):
        _error_copy_failed()
    try:
        directory.resolve().relative_to(trusted_root)
    except ValueError:
        _error_copy_failed()
    if directory.is_dir():
        shutil.rmtree(directory)
    else:
        _error_copy_failed()


def _validate_prepared_paths(prepared):
    if prepared.final_directory.name != str(prepared.record_id):
        _error_copy_failed()
    root = prepared.final_directory.parent
    if prepared.storage_root is None or _is_link(root) or root.resolve() != prepared.storage_root:
        _error_copy_failed()
    if prepared.staging_directory is not None:
        if (
            prepared.staging_directory.name != f"{prepared.record_id}-{prepared.operation_id}"
            or prepared.staging_directory.parent != root / ".staging"
            or _is_link(root / ".staging")
        ):
            _error_copy_failed()


def prepare_record_image_copies(record_id, submissions, *, task_image_root, record_image_root):
    _require_record_id(record_id)
    root = Path(record_image_root)
    operation_id = uuid4().hex
    final_directory = root / str(record_id)
    image_submissions = [item for item in submissions if getattr(item, "image_url", None)]
    for item in image_submissions:
        if not isinstance(item.id, int) or isinstance(item.id, bool) or item.id < 1:
            _error_copy_failed()
    ordered_submissions = sorted(image_submissions, key=lambda item: item.id)
    if not ordered_submissions:
        return PreparedRecordImageCopies(record_id, operation_id, None, final_directory, {}, (), storage_root=root.resolve())

    source_info = {}
    for item in ordered_submissions:
        source_key = item.image_url
        if source_key in source_info:
            continue
        source = _task_source_path(task_image_root, source_key)
        try:
            data = source.read_bytes()
        except OSError:
            _error_source_missing()
        if not data:
            _error_source_missing()
        extension, content_type = _detect_image_type(data)
        source_info[source_key] = (source, len(data), extension, content_type)

    staging_directory = root / ".staging" / f"{record_id}-{operation_id}"
    assets_by_source = {}
    staged_files = []
    if _is_link(root) or _is_link(root / ".staging"):
        _error_copy_failed()
    try:
        staging_directory.mkdir(parents=True, exist_ok=False)
        if _is_link(root) or _is_link(root / ".staging"):
            _error_copy_failed()
        for index, (source_key, (source, source_size, extension, content_type)) in enumerate(source_info.items(), start=1):
            filename = f"{uuid4().hex}{extension}"
            staged_path = staging_directory / filename
            shutil.copyfile(source, staged_path)
            data = staged_path.read_bytes()
            if not data or len(data) != source_size:
                _error_copy_failed()
            try:
                verified_extension, verified_content_type = _detect_image_type(data)
            except JourneyRecordImageError:
                _error_copy_failed()
            if (verified_extension, verified_content_type) != (extension, content_type):
                _error_copy_failed()
            asset = {
                "id": f"img-{index:02d}",
                "storageKey": f"record-images/{record_id}/{filename}",
                "contentType": content_type,
                "byteSize": len(data),
            }
            assets_by_source[source_key] = asset
            staged_files.append(staged_path)
    except JourneyRecordImageError:
        _remove_owned_directory(staging_directory, root / ".staging", root.resolve())
        raise
    except OSError:
        _remove_owned_directory(staging_directory, root / ".staging", root.resolve())
        _error_copy_failed()

    return PreparedRecordImageCopies(
        record_id,
        operation_id,
        staging_directory,
        final_directory,
        {item.id: deepcopy(assets_by_source[item.image_url]) for item in ordered_submissions},
        tuple(staged_files),
        storage_root=root.resolve(),
    )


def publish_record_image_copies(prepared):
    if not isinstance(prepared, PreparedRecordImageCopies):
        _error_copy_failed()
    _validate_prepared_paths(prepared)
    if prepared.published:
        return deepcopy(prepared.assets_by_submission_id)
    if prepared.staging_directory is None:
        prepared.published = True
        return {}
    if not prepared.staging_directory.is_dir() or prepared.staging_directory.is_symlink() or prepared.final_directory.exists():
        _error_copy_failed()
    try:
        os.rename(prepared.staging_directory, prepared.final_directory)
    except OSError:
        _error_copy_failed()
    prepared.published = True
    return deepcopy(prepared.assets_by_submission_id)


def cleanup_record_image_copies(prepared, *, remove_published=False):
    if not isinstance(prepared, PreparedRecordImageCopies):
        _error_copy_failed()
    _validate_prepared_paths(prepared)
    root = prepared.final_directory.parent
    if not prepared.published:
        _remove_owned_directory(prepared.staging_directory, root / ".staging", prepared.storage_root)
    elif remove_published:
        _remove_owned_directory(prepared.final_directory, root, prepared.storage_root)


def resolve_record_image_asset(record, asset_id, *, record_image_root):
    snapshot = getattr(record, "snapshot", None)
    if not snapshot:
        _error_not_found()
    try:
        validated_snapshot = validate_journey_record_snapshot(snapshot)
    except JourneyRecordSnapshotValidationError:
        raise JourneyRecordImageError(
            "JOURNEY_RECORD_SNAPSHOT_INVALID",
            "Journey record snapshot is invalid",
            500,
        ) from None
    asset = next((item for item in validated_snapshot["imageAssets"] if item["id"] == asset_id), None)
    if asset is None:
        _error_not_found()
    path = _record_asset_path(record_image_root, record.id, asset["storageKey"])
    try:
        data = path.read_bytes()
    except OSError:
        _error_not_found()
    if len(data) != asset["byteSize"]:
        _error_not_found()
    try:
        _, content_type = _detect_image_type(data)
    except JourneyRecordImageError:
        _error_not_found()
    if content_type != asset["contentType"]:
        _error_not_found()
    return path, content_type, path.name
