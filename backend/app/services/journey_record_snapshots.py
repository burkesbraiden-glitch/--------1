from copy import deepcopy
from datetime import datetime


SNAPSHOT_SCHEMA_VERSION = 1
_ALLOWED_IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}


class JourneyRecordSnapshotValidationError(ValueError):
    pass


def _fail(message):
    raise JourneyRecordSnapshotValidationError(message)


def _is_positive_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _require_positive_int(value, path):
    if not _is_positive_int(value):
        _fail(f"{path} must be a positive integer")
    return value


def _require_string(value, path, *, allow_none=False):
    if value is None and allow_none:
        return value
    if not isinstance(value, str):
        _fail(f"{path} must be a string")
    return value


def _format_datetime(value, path):
    if not isinstance(value, datetime) or value.tzinfo is not None:
        _fail(f"{path} must be a UTC naive datetime")
    return f"{value.isoformat()}Z"


def _has_note(submission):
    return bool(submission and isinstance(submission.note, str) and submission.note.strip())


def _asset_for_submission(image_assets_by_submission_id, submission):
    if not submission.image_url:
        return None
    return image_assets_by_submission_id.get(submission.id)


def build_journey_record_snapshot_v1(
    record,
    plan,
    tasks,
    *,
    finalized_at,
    image_assets_by_submission_id=None,
):
    if not isinstance(image_assets_by_submission_id, (dict, type(None))):
        _fail("image_assets_by_submission_id must be a dict or None")
    image_assets_by_submission_id = image_assets_by_submission_id or {}
    finalized_at_text = _format_datetime(finalized_at, "finalized_at")
    task_list = sorted(list(tasks), key=lambda task: (task.sort_order, task.id))

    for task in task_list:
        if getattr(task, "submission", None) is None:
            _fail("task.submission is required")

    asset_ids_by_submission_id = {}
    image_assets = []
    for task in task_list:
        submission = task.submission
        asset = _asset_for_submission(image_assets_by_submission_id, submission)
        if asset is None:
            continue
        asset_ids_by_submission_id[submission.id] = asset.get("id") if isinstance(asset, dict) else None
        image_assets.append(deepcopy(asset))

    custom_title = record.custom_title
    display_title = custom_title if isinstance(custom_title, str) and custom_title.strip() else plan.title
    entries = [
        {
            "taskId": task.id,
            "submissionId": task.submission.id,
            "title": task.title,
            "subtitle": task.subtitle,
            "sortOrder": task.sort_order,
            "status": task.submission.status,
            "note": task.submission.note or "",
            "completedAt": _format_datetime(task.submission.completed_at, "submission.completed_at")
            if task.submission.completed_at is not None
            else None,
            "imageAssetId": asset_ids_by_submission_id.get(task.submission.id),
        }
        for task in task_list
    ]
    submissions = [task.submission for task in task_list]
    cover_asset_id = asset_ids_by_submission_id.get(record.cover_submission_id)
    snapshot = {
        "schemaVersion": SNAPSHOT_SCHEMA_VERSION,
        "record": {
            "id": record.id,
            "planId": record.plan_id,
            "childId": plan.child_id,
            "title": plan.title,
            "customTitle": custom_title,
            "displayTitle": display_title,
            "destination": plan.destination,
            "planStatus": plan.status,
            "status": "finalized",
            "summary": record.summary,
            "coverSubmissionId": record.cover_submission_id,
            "taskCount": len(task_list),
            "completedTaskCount": sum(submission.status == "completed" for submission in submissions),
            "photoCount": sum(bool(submission.image_url) for submission in submissions),
            "noteCount": sum(_has_note(submission) for submission in submissions),
            "finalizedAt": finalized_at_text,
            "createdAt": _format_datetime(record.created_at, "record.created_at"),
            "updatedAt": finalized_at_text,
        },
        "cover": {
            "submissionId": record.cover_submission_id,
            "imageAssetId": cover_asset_id,
        },
        "entries": entries,
        "imageAssets": image_assets,
    }
    return validate_journey_record_snapshot(snapshot)


def _require_exact_keys(payload, keys, path):
    if not isinstance(payload, dict):
        _fail(f"{path} must be a dict")
    for key in keys:
        if key not in payload:
            _fail(f"{path}.{key} is required")
    if set(payload) - set(keys):
        _fail(f"{path} has unknown fields")


def _validate_storage_key(storage_key, record_id, path):
    if not isinstance(storage_key, str):
        _fail(f"{path} is invalid")
    prefix = f"record-images/{record_id}/"
    parts = storage_key.split("/")
    if (
        not storage_key.startswith(prefix)
        or "\\" in storage_key
        or any(part in {"", ".", ".."} for part in parts)
    ):
        _fail(f"{path} is invalid")


def _validate_asset(asset, index, record_id, asset_ids):
    path = f"snapshot.imageAssets[{index}]"
    _require_exact_keys(asset, {"id", "storageKey", "contentType", "byteSize"}, path)
    asset_id = asset["id"]
    if not isinstance(asset_id, str) or not asset_id.strip():
        _fail(f"{path}.id must be a non-empty string")
    if asset_id in asset_ids:
        _fail(f"{path}.id must be unique")
    asset_ids.add(asset_id)
    _validate_storage_key(asset["storageKey"], record_id, f"{path}.storageKey")
    if asset["contentType"] not in _ALLOWED_IMAGE_CONTENT_TYPES:
        _fail(f"{path}.contentType is invalid")
    if not _is_positive_int(asset["byteSize"]):
        _fail(f"{path}.byteSize must be a positive integer")


def _validate_asset_reference(value, asset_ids, path):
    if value is None:
        return
    if not isinstance(value, str) or value not in asset_ids:
        _fail(f"{path} is unknown")


def validate_journey_record_snapshot(snapshot):
    if not isinstance(snapshot, dict):
        _fail("snapshot must be a dict")
    _require_exact_keys(snapshot, ("schemaVersion", "record", "cover", "entries", "imageAssets"), "snapshot")
    if not isinstance(snapshot["schemaVersion"], int) or isinstance(snapshot["schemaVersion"], bool):
        _fail("snapshot.schemaVersion must be an integer")
    if snapshot["schemaVersion"] != SNAPSHOT_SCHEMA_VERSION:
        _fail("snapshot.schemaVersion is unsupported")

    record = snapshot["record"]
    record_keys = {
        "id", "planId", "childId", "title", "customTitle", "displayTitle", "destination", "planStatus",
        "status", "summary", "coverSubmissionId", "taskCount", "completedTaskCount", "photoCount", "noteCount",
        "finalizedAt", "createdAt", "updatedAt",
    }
    _require_exact_keys(record, record_keys, "snapshot.record")
    for key in ("id", "planId", "childId"):
        _require_positive_int(record[key], f"snapshot.record.{key}")
    for key in ("title", "displayTitle", "destination", "planStatus", "finalizedAt", "createdAt", "updatedAt"):
        _require_string(record[key], f"snapshot.record.{key}")
    for key in ("customTitle", "summary"):
        _require_string(record[key], f"snapshot.record.{key}", allow_none=True)
    if record["status"] != "finalized":
        _fail("snapshot.record.status must be finalized")
    if record["coverSubmissionId"] is not None:
        _require_positive_int(record["coverSubmissionId"], "snapshot.record.coverSubmissionId")
    for key in ("taskCount", "completedTaskCount", "photoCount", "noteCount"):
        if not isinstance(record[key], int) or isinstance(record[key], bool) or record[key] < 0:
            _fail(f"snapshot.record.{key} must be a non-negative integer")

    image_assets = snapshot["imageAssets"]
    if not isinstance(image_assets, list):
        _fail("snapshot.imageAssets must be a list")
    asset_ids = set()
    for index, asset in enumerate(image_assets):
        _validate_asset(asset, index, record["id"], asset_ids)

    entries = snapshot["entries"]
    if not isinstance(entries, list):
        _fail("snapshot.entries must be a list")
    entry_keys = {"taskId", "submissionId", "title", "subtitle", "sortOrder", "status", "note", "completedAt", "imageAssetId"}
    entry_asset_ids_by_submission_id = {}
    for index, entry in enumerate(entries):
        path = f"snapshot.entries[{index}]"
        _require_exact_keys(entry, entry_keys, path)
        for key in ("taskId", "submissionId", "sortOrder"):
            _require_positive_int(entry[key], f"{path}.{key}")
        for key in ("title", "status", "note"):
            _require_string(entry[key], f"{path}.{key}")
        _require_string(entry["subtitle"], f"{path}.subtitle", allow_none=True)
        _require_string(entry["completedAt"], f"{path}.completedAt", allow_none=True)
        _validate_asset_reference(entry["imageAssetId"], asset_ids, f"{path}.imageAssetId")
        entry_asset_ids_by_submission_id[entry["submissionId"]] = entry["imageAssetId"]

    cover = snapshot["cover"]
    _require_exact_keys(cover, {"submissionId", "imageAssetId"}, "snapshot.cover")
    if cover["submissionId"] is not None:
        _require_positive_int(cover["submissionId"], "snapshot.cover.submissionId")
    _validate_asset_reference(cover["imageAssetId"], asset_ids, "snapshot.cover.imageAssetId")
    if cover["submissionId"] != record["coverSubmissionId"]:
        _fail("snapshot.cover.submissionId must match snapshot.record.coverSubmissionId")
    if cover["submissionId"] is None:
        if cover["imageAssetId"] is not None:
            _fail("snapshot.cover.imageAssetId must be null without a submission")
    elif entry_asset_ids_by_submission_id.get(cover["submissionId"]) != cover["imageAssetId"]:
        _fail("snapshot.cover.imageAssetId must match its entry")

    return deepcopy(snapshot)
