from copy import deepcopy
from datetime import datetime
import re
from types import SimpleNamespace

import pytest

from app.services.journey_record_snapshots import (
    JourneyRecordSnapshotValidationError,
    SNAPSHOT_SCHEMA_VERSION,
    build_journey_record_snapshot_v1,
    validate_journey_record_snapshot,
)


FINALIZED_AT = datetime(2026, 8, 6, 10, 0, 0)
CREATED_AT = datetime(2026, 8, 1, 9, 0, 0)
COMPLETED_AT = datetime(2026, 8, 5, 11, 30, 0)


def make_task(task_id, sort_order, *, submission):
    return SimpleNamespace(
        id=task_id,
        sort_order=sort_order,
        title=f"任务 {task_id}",
        subtitle=f"任务 {task_id} 的观察",
        submission=submission,
    )


def make_submission(submission_id, *, image_url=None, note="", status="completed", completed_at=COMPLETED_AT):
    return SimpleNamespace(
        id=submission_id,
        image_url=image_url,
        note=note,
        status=status,
        completed_at=completed_at,
    )


def snapshot_inputs():
    record = SimpleNamespace(
        id=1000,
        plan_id=100,
        custom_title="  第一次故宫旅行  ",
        summary="我发现了屋顶小兽。",
        cover_submission_id=5501,
        created_at=CREATED_AT,
    )
    plan = SimpleNamespace(id=100, child_id=10, title="故宫亲子探索", destination="故宫博物院", status="completed")
    first = make_task(501, 2, submission=make_submission(5501, image_url="task-images/source-a.jpg", note="发现一"))
    second = make_task(502, 1, submission=make_submission(5502, image_url=None, note="发现二"))
    third = make_task(503, 3, submission=make_submission(5503, image_url="task-images/source-c.png", note="   ", status="in-progress", completed_at=None))
    assets = {
        5501: {
            "id": "img-01",
            "storageKey": "record-images/1000/first.jpg",
            "contentType": "image/jpeg",
            "byteSize": 123456,
        },
        5503: {
            "id": "img-03",
            "storageKey": "record-images/1000/third.png",
            "contentType": "image/png",
            "byteSize": 234567,
        },
    }
    return record, plan, [first, second, third], assets


def build_valid_snapshot():
    record, plan, tasks, assets = snapshot_inputs()
    return build_journey_record_snapshot_v1(
        record,
        plan,
        tasks,
        finalized_at=FINALIZED_AT,
        image_assets_by_submission_id=assets,
    )


def test_builder_creates_sorted_independent_snapshot_with_current_aggregate_semantics():
    record, plan, tasks, assets = snapshot_inputs()

    snapshot = build_journey_record_snapshot_v1(
        record,
        plan,
        tasks,
        finalized_at=FINALIZED_AT,
        image_assets_by_submission_id=assets,
    )

    assert snapshot["schemaVersion"] == SNAPSHOT_SCHEMA_VERSION == 1
    assert snapshot["record"] == {
        "id": 1000,
        "planId": 100,
        "childId": 10,
        "title": "故宫亲子探索",
        "customTitle": "  第一次故宫旅行  ",
        "displayTitle": "  第一次故宫旅行  ",
        "destination": "故宫博物院",
        "planStatus": "completed",
        "status": "finalized",
        "summary": "我发现了屋顶小兽。",
        "coverSubmissionId": 5501,
        "taskCount": 3,
        "completedTaskCount": 2,
        "photoCount": 2,
        "noteCount": 2,
        "finalizedAt": "2026-08-06T10:00:00Z",
        "createdAt": "2026-08-01T09:00:00Z",
        "updatedAt": "2026-08-06T10:00:00Z",
    }
    assert [entry["taskId"] for entry in snapshot["entries"]] == [502, 501, 503]
    assert snapshot["cover"] == {"submissionId": 5501, "imageAssetId": "img-01"}
    assert snapshot["entries"][1]["imageAssetId"] == "img-01"
    assert snapshot["entries"][0]["imageAssetId"] is None
    assert snapshot["imageAssets"] == [assets[5501], assets[5503]]

    record.custom_title = "改后的标题"
    tasks[0].submission.note = "改后的发现"
    assets[5501]["byteSize"] = 1
    assert snapshot["record"]["displayTitle"] == "  第一次故宫旅行  "
    assert snapshot["entries"][1]["note"] == "发现一"
    assert snapshot["imageAssets"][0]["byteSize"] == 123456


def test_builder_uses_plan_title_for_blank_custom_title_and_allows_no_cover_or_images():
    record, plan, _, _ = snapshot_inputs()
    record.custom_title = "   "
    record.cover_submission_id = None
    tasks = [make_task(501, 1, submission=make_submission(5501, image_url=None, note="", status="in-progress", completed_at=None))]

    snapshot = build_journey_record_snapshot_v1(record, plan, tasks, finalized_at=FINALIZED_AT)

    assert snapshot["record"]["displayTitle"] == plan.title
    assert snapshot["record"]["photoCount"] == 0
    assert snapshot["cover"] == {"submissionId": None, "imageAssetId": None}
    assert snapshot["entries"][0]["imageAssetId"] is None
    assert snapshot["imageAssets"] == []


@pytest.mark.parametrize(
    "tasks, finalized_at",
    [([SimpleNamespace(id=501, sort_order=1, submission=None)], FINALIZED_AT), ([], None)],
)
def test_builder_rejects_missing_submission_or_finalized_time(tasks, finalized_at):
    record, plan, _, _ = snapshot_inputs()

    with pytest.raises(JourneyRecordSnapshotValidationError):
        build_journey_record_snapshot_v1(record, plan, tasks, finalized_at=finalized_at)


def test_validator_returns_a_deep_copy_without_mutating_the_input():
    snapshot = build_valid_snapshot()
    original = deepcopy(snapshot)

    validated = validate_journey_record_snapshot(snapshot)
    validated["record"]["title"] = "其他标题"
    validated["imageAssets"][0]["byteSize"] = 1

    assert snapshot == original


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda snapshot: snapshot.clear(), "snapshot.schemaVersion is required"),
        (lambda snapshot: snapshot.__setitem__("schemaVersion", 2), "snapshot.schemaVersion is unsupported"),
        (lambda snapshot: snapshot.__setitem__("schemaVersion", True), "snapshot.schemaVersion must be an integer"),
        (lambda snapshot: snapshot.__setitem__("unexpected", True), "snapshot has unknown fields"),
        (lambda snapshot: snapshot["record"].__setitem__("status", "draft"), "snapshot.record.status must be finalized"),
        (lambda snapshot: snapshot["record"].__setitem__("id", "1000"), "snapshot.record.id must be a positive integer"),
        (lambda snapshot: snapshot.__setitem__("entries", {}), "snapshot.entries must be a list"),
        (lambda snapshot: snapshot["imageAssets"].append(deepcopy(snapshot["imageAssets"][0])), "snapshot.imageAssets[2].id must be unique"),
        (lambda snapshot: snapshot["entries"][0].__setitem__("imageAssetId", "unknown"), "snapshot.entries[0].imageAssetId is unknown"),
        (lambda snapshot: snapshot["cover"].__setitem__("imageAssetId", "unknown"), "snapshot.cover.imageAssetId is unknown"),
        (lambda snapshot: snapshot["cover"].__setitem__("submissionId", 5502), "snapshot.cover.submissionId must match snapshot.record.coverSubmissionId"),
        (lambda snapshot: snapshot["imageAssets"][0].__setitem__("storageKey", "C:/records/photo.jpg"), "snapshot.imageAssets[0].storageKey is invalid"),
        (lambda snapshot: snapshot["imageAssets"][0].__setitem__("storageKey", "record-images/1000/../photo.jpg"), "snapshot.imageAssets[0].storageKey is invalid"),
        (lambda snapshot: snapshot["imageAssets"][0].__setitem__("storageKey", "record-images\\1000\\photo.jpg"), "snapshot.imageAssets[0].storageKey is invalid"),
        (lambda snapshot: snapshot["imageAssets"][0].__setitem__("storageKey", "record-images/999/photo.jpg"), "snapshot.imageAssets[0].storageKey is invalid"),
        (lambda snapshot: snapshot["imageAssets"][0].__setitem__("contentType", "image/gif"), "snapshot.imageAssets[0].contentType is invalid"),
        (lambda snapshot: snapshot["imageAssets"][0].__setitem__("byteSize", 0), "snapshot.imageAssets[0].byteSize must be a positive integer"),
    ],
)
def test_validator_rejects_invalid_v1_contracts(mutate, message):
    snapshot = build_valid_snapshot()
    mutate(snapshot)

    with pytest.raises(JourneyRecordSnapshotValidationError, match=re.escape(message)):
        validate_journey_record_snapshot(snapshot)


def test_validator_rejects_non_dict_snapshot():
    with pytest.raises(JourneyRecordSnapshotValidationError, match="snapshot must be a dict"):
        validate_journey_record_snapshot([])
