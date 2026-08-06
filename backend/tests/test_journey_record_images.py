from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import re

import pytest


PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
JPEG_BYTES = b"\xff\xd8\xff\xe0jpeg-body"
WEBP_BYTES = b"RIFF\x10\x00\x00\x00WEBPVP8 "


def submission(submission_id, image_url):
    return SimpleNamespace(id=submission_id, image_url=image_url)


def write_source(root, filename, data):
    root.mkdir(parents=True, exist_ok=True)
    path = root / filename
    path.write_bytes(data)
    return path


def snapshot(record_id, assets):
    image_asset_ids = {asset["id"] for asset in assets}
    return {
        "schemaVersion": 1,
        "record": {
            "id": record_id, "planId": 11, "childId": 12, "title": "Plan",
            "customTitle": None, "displayTitle": "Plan", "destination": "Museum",
            "planStatus": "completed", "status": "finalized", "summary": None,
            "coverSubmissionId": None, "taskCount": 0, "completedTaskCount": 0,
            "photoCount": 0, "noteCount": 0, "finalizedAt": "2026-08-06T00:00:00Z",
            "createdAt": "2026-08-06T00:00:00Z", "updatedAt": "2026-08-06T00:00:00Z",
        },
        "cover": {"submissionId": None, "imageAssetId": None},
        "entries": [],
        "imageAssets": assets if image_asset_ids else [],
    }


def test_config_has_independent_record_image_roots():
    from app.config import BACKEND_DIR, BaseConfig, TestingConfig

    assert Path(BaseConfig.RECORD_IMAGE_UPLOAD_DIR) == BACKEND_DIR / "var" / "uploads" / "record-images"
    assert Path(TestingConfig.RECORD_IMAGE_UPLOAD_DIR) == BACKEND_DIR / "var" / "testing-uploads" / "record-images"


@pytest.mark.parametrize(
    ("data", "extension", "content_type"),
    ((PNG_BYTES, ".png", "image/png"), (JPEG_BYTES, ".jpg", "image/jpeg"), (WEBP_BYTES, ".webp", "image/webp")),
)
def test_prepare_copies_supported_images_to_private_staging(tmp_path, data, extension, content_type):
    from app.services.journey_record_images import prepare_record_image_copies

    task_root = tmp_path / "task-images"
    source = write_source(task_root, "source.bin", data)
    prepared = prepare_record_image_copies(
        1000, [submission(8, "task-images/source.bin")], task_image_root=task_root, record_image_root=tmp_path / "record-images"
    )

    asset = prepared.assets_by_submission_id[8]
    assert prepared.final_directory == tmp_path / "record-images" / "1000"
    assert prepared.staging_directory.parent == tmp_path / "record-images" / ".staging"
    assert asset["contentType"] == content_type
    assert asset["storageKey"].startswith("record-images/1000/")
    assert asset["storageKey"].endswith(extension)
    assert re.fullmatch(r"record-images/1000/[0-9a-f]{32}" + re.escape(extension), asset["storageKey"])
    assert prepared.staged_files[0].read_bytes() == source.read_bytes()
    assert prepared.staged_files[0].parent == prepared.staging_directory


def test_prepare_deduplicates_source_and_returns_independent_asset_values(tmp_path):
    from app.services.journey_record_images import prepare_record_image_copies

    task_root = tmp_path / "task-images"
    write_source(task_root, "same.png", PNG_BYTES)
    prepared = prepare_record_image_copies(
        1000,
        [submission(20, "task-images/same.png"), submission(10, "task-images/same.png")],
        task_image_root=task_root,
        record_image_root=tmp_path / "record-images",
    )

    first, second = prepared.assets_by_submission_id[10], prepared.assets_by_submission_id[20]
    assert len(prepared.staged_files) == 1
    assert first == second
    assert first is not second
    first["id"] = "changed"
    assert second["id"] == "img-01"


@pytest.mark.parametrize("key", ("/tmp/a.png", "task-images/../a.png", "task-images/a/b.png", "task-images\\a.png", "other-images/a.png"))
def test_prepare_rejects_unsafe_or_missing_sources_without_leaking_paths(tmp_path, key):
    from app.services.journey_record_images import JourneyRecordImageError, prepare_record_image_copies

    task_root = tmp_path / "task-images"
    write_source(task_root, "safe.png", PNG_BYTES)
    with pytest.raises(JourneyRecordImageError) as raised:
        prepare_record_image_copies(1000, [submission(1, key)], task_image_root=task_root, record_image_root=tmp_path / "record-images")

    assert raised.value.code == "JOURNEY_RECORD_SOURCE_IMAGE_MISSING"
    assert str(task_root) not in raised.value.message


@pytest.mark.parametrize("data", (b"", b"GIF89a"))
def test_prepare_rejects_empty_or_unsupported_source(tmp_path, data):
    from app.services.journey_record_images import JourneyRecordImageError, prepare_record_image_copies

    task_root = tmp_path / "task-images"
    write_source(task_root, "source", data)
    with pytest.raises(JourneyRecordImageError) as raised:
        prepare_record_image_copies(1000, [submission(1, "task-images/source")], task_image_root=task_root, record_image_root=tmp_path / "record-images")
    assert raised.value.code == "JOURNEY_RECORD_SOURCE_IMAGE_MISSING"


def test_publish_and_cleanup_only_touch_the_prepared_operation(tmp_path):
    from app.services.journey_record_images import cleanup_record_image_copies, prepare_record_image_copies, publish_record_image_copies

    task_root = tmp_path / "task-images"
    write_source(task_root, "source.png", PNG_BYTES)
    record_root = tmp_path / "record-images"
    prepared = prepare_record_image_copies(1000, [submission(1, "task-images/source.png")], task_image_root=task_root, record_image_root=record_root)
    returned = publish_record_image_copies(prepared)

    assert prepared.published is True
    assert not prepared.staging_directory.exists()
    assert prepared.final_directory.exists()
    assert returned == prepared.assets_by_submission_id
    returned[1]["id"] = "outside-mutation"
    assert prepared.assets_by_submission_id[1]["id"] == "img-01"
    cleanup_record_image_copies(prepared)
    assert prepared.final_directory.exists()
    cleanup_record_image_copies(prepared, remove_published=True)
    cleanup_record_image_copies(prepared, remove_published=True)
    assert not prepared.final_directory.exists()


def test_empty_prepare_publish_is_idempotent_without_creating_directories(tmp_path):
    from app.services.journey_record_images import prepare_record_image_copies, publish_record_image_copies

    root = tmp_path / "record-images"
    prepared = prepare_record_image_copies(1000, [], task_image_root=tmp_path / "task-images", record_image_root=root)
    assert prepared.staging_directory is None
    assert publish_record_image_copies(prepared) == {}
    assert publish_record_image_copies(prepared) == {}
    assert not root.exists()


def test_prepare_copy_failure_removes_its_staging_operation(tmp_path, monkeypatch):
    import app.services.journey_record_images as images

    task_root = tmp_path / "task-images"
    write_source(task_root, "source.png", PNG_BYTES)
    monkeypatch.setattr(images.shutil, "copyfile", lambda *_: (_ for _ in ()).throw(OSError("copy failed")))

    with pytest.raises(images.JourneyRecordImageError) as raised:
        images.prepare_record_image_copies(
            1000, [submission(1, "task-images/source.png")], task_image_root=task_root, record_image_root=tmp_path / "record-images"
        )
    assert raised.value.code == "RECORD_IMAGE_COPY_FAILED"
    assert not list((tmp_path / "record-images" / ".staging").glob("1000-*"))


def test_prepare_rejects_a_staged_copy_with_a_different_size(tmp_path, monkeypatch):
    import app.services.journey_record_images as images

    task_root = tmp_path / "task-images"
    source = write_source(task_root, "source.png", PNG_BYTES)

    def copy_wrong_size(_, target):
        Path(target).write_bytes(source.read_bytes() + b"extra")

    monkeypatch.setattr(images.shutil, "copyfile", copy_wrong_size)
    with pytest.raises(images.JourneyRecordImageError) as raised:
        images.prepare_record_image_copies(
            1000, [submission(1, "task-images/source.png")], task_image_root=task_root, record_image_root=tmp_path / "record-images"
        )
    assert raised.value.code == "RECORD_IMAGE_COPY_FAILED"
    assert not list((tmp_path / "record-images" / ".staging").glob("1000-*"))


def test_publish_refuses_an_existing_final_directory_without_overwriting(tmp_path):
    from app.services.journey_record_images import JourneyRecordImageError, prepare_record_image_copies, publish_record_image_copies

    task_root = tmp_path / "task-images"
    write_source(task_root, "source.png", PNG_BYTES)
    root = tmp_path / "record-images"
    prepared = prepare_record_image_copies(1000, [submission(1, "task-images/source.png")], task_image_root=task_root, record_image_root=root)
    prepared.final_directory.mkdir(parents=True)
    marker = prepared.final_directory / "existing.txt"
    marker.write_text("keep")

    with pytest.raises(JourneyRecordImageError) as raised:
        publish_record_image_copies(prepared)
    assert raised.value.code == "RECORD_IMAGE_COPY_FAILED"
    assert marker.read_text() == "keep"
    assert prepared.staging_directory.exists()


def test_cleanup_rejects_a_tampered_operation_path_without_touching_an_outside_directory(tmp_path):
    from app.services.journey_record_images import (
        JourneyRecordImageError,
        PreparedRecordImageCopies,
        cleanup_record_image_copies,
    )

    outside = tmp_path / "outside"
    outside.mkdir()
    prepared = PreparedRecordImageCopies(
        1000, "a" * 32, None, outside, {}, (), published=True, storage_root=(tmp_path / "record-images").resolve()
    )
    with pytest.raises(JourneyRecordImageError):
        cleanup_record_image_copies(prepared, remove_published=True)
    assert outside.exists()


def test_cleanup_rejects_a_linked_staging_ancestor_before_recursive_delete(tmp_path, monkeypatch):
    import app.services.journey_record_images as images

    task_root = tmp_path / "task-images"
    write_source(task_root, "source.png", PNG_BYTES)
    prepared = images.prepare_record_image_copies(
        1000, [submission(1, "task-images/source.png")], task_image_root=task_root, record_image_root=tmp_path / "record-images"
    )
    original_is_link = images._is_link
    monkeypatch.setattr(images, "_is_link", lambda path: path == prepared.staging_directory.parent or original_is_link(path))

    with pytest.raises(images.JourneyRecordImageError):
        images.cleanup_record_image_copies(prepared)
    assert prepared.staging_directory.exists()


def test_resolve_rechecks_snapshot_size_type_and_private_path(tmp_path):
    from app.services.journey_record_images import JourneyRecordImageError, resolve_record_image_asset

    root = tmp_path / "record-images"
    path = write_source(root / "1000", "asset.png", PNG_BYTES)
    asset = {"id": "img-01", "storageKey": "record-images/1000/asset.png", "contentType": "image/png", "byteSize": len(PNG_BYTES)}
    record = SimpleNamespace(id=1000, snapshot=snapshot(1000, [asset]))
    image_path, content_type, filename = resolve_record_image_asset(record, "img-01", record_image_root=root)

    assert image_path == path
    assert content_type == "image/png"
    assert filename == "asset.png"
    path.write_bytes(JPEG_BYTES)
    with pytest.raises(JourneyRecordImageError) as raised:
        resolve_record_image_asset(record, "img-01", record_image_root=root)
    assert raised.value.code == "JOURNEY_RECORD_IMAGE_NOT_FOUND"


def test_resolve_maps_invalid_snapshot_and_unknown_asset_to_safe_errors(tmp_path):
    from app.services.journey_record_images import JourneyRecordImageError, resolve_record_image_asset

    invalid_record = SimpleNamespace(id=1000, snapshot={"schemaVersion": 1})
    with pytest.raises(JourneyRecordImageError) as invalid:
        resolve_record_image_asset(invalid_record, "img-01", record_image_root=tmp_path)
    assert invalid.value.code == "JOURNEY_RECORD_SNAPSHOT_INVALID"

    record = SimpleNamespace(id=1000, snapshot=snapshot(1000, []))
    with pytest.raises(JourneyRecordImageError) as missing:
        resolve_record_image_asset(record, "img-01", record_image_root=tmp_path)
    assert missing.value.code == "JOURNEY_RECORD_IMAGE_NOT_FOUND"
