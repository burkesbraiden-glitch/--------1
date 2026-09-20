import importlib.util
from pathlib import Path

import pytest

from app.models import GuideCard


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations" / "versions"


def job_migration_path():
    matches = list(MIGRATIONS_DIR.glob("*_add_guide_audio_jobs.py"))
    if not matches:
        pytest.fail("P8.2B2 migration contract is missing: *_add_guide_audio_jobs.py")
    assert len(matches) == 1
    return matches[0]


def load_migration():
    path = job_migration_path()
    spec = importlib.util.spec_from_file_location("guide_audio_jobs_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RecordingOp:
    def __init__(self):
        self.calls = []

    def create_table(self, name, *columns, **kwargs):
        self.calls.append(("create_table", name, columns, kwargs))

    def drop_table(self, name, **kwargs):
        self.calls.append(("drop_table", name, (), kwargs))

    def create_index(self, name, table_name, columns, **kwargs):
        self.calls.append(("create_index", name, table_name, tuple(columns), kwargs))

    def drop_index(self, name, table_name=None, **kwargs):
        self.calls.append(("drop_index", name, table_name, kwargs))


def test_audio_job_migration_is_additive_after_p8b1_audio_domain():
    migration = load_migration()
    source = job_migration_path().read_text(encoding="utf-8")

    assert migration.down_revision == "f8e7d6c5b4a3"
    assert "guide_audio_jobs" in source
    assert "alter_table(\"guide_cards\")" not in source
    assert "batch_alter_table(\"guide_cards\")" not in source
    assert "drop_column" not in source.split("def downgrade", 1)[0]
    for field in (
        "guide_id",
        "guide_version",
        "source_hash",
        "generation_token",
        "status",
        "attempt_count",
        "available_at",
        "claimed_at",
        "lease_expires_at",
        "finished_at",
        "provider_job_id",
        "last_error_code",
        "created_at",
        "updated_at",
    ):
        assert field in source


def test_audio_job_migration_upgrade_downgrade_and_reupgrade_keep_job_table_contract(monkeypatch):
    migration = load_migration()
    recorder = RecordingOp()
    monkeypatch.setattr(migration, "op", recorder)

    migration.upgrade()
    migration.downgrade()
    migration.upgrade()

    create_table_calls = [call for call in recorder.calls if call[0] == "create_table"]
    create_index_calls = [call for call in recorder.calls if call[0] == "create_index"]
    assert len(create_table_calls) == 2
    assert all(call[1] == "guide_audio_jobs" for call in create_table_calls)
    assert any(call[1] == "ix_guide_audio_jobs_status_available_id" for call in create_index_calls)
    assert any(call[0] == "drop_index" and call[1] == "ix_guide_audio_jobs_status_available_id" for call in recorder.calls)
    assert any(call[0] == "drop_table" and call[1] == "guide_audio_jobs" for call in recorder.calls)


def test_audio_job_migration_does_not_change_existing_guide_card_audio_columns():
    table = GuideCard.__table__

    for field in (
        "narration_text",
        "guide_version",
        "audio_status",
        "audio_object_key",
        "audio_source_hash",
        "audio_generation_token",
        "audio_duration_sec",
        "audio_generated_at",
        "audio_error_code",
        "audio_url",
    ):
        assert field in table.c
