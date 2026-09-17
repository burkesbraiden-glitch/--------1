import importlib.util
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "f8e7d6c5b4a3_add_guide_audio_domain.py"
)


def load_migration():
    spec = importlib.util.spec_from_file_location("guide_audio_migration", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_guide_audio_migration_is_additive_and_preserves_legacy_audio_url():
    migration = load_migration()
    source = MIGRATION_PATH.read_text(encoding="utf-8")
    upgrade_source = source.split("def downgrade", 1)[0]

    assert migration.revision == "f8e7d6c5b4a3"
    assert migration.down_revision == "ea8f05d3f3af"
    assert "drop_column" not in upgrade_source
    assert "audio_url" not in source.replace("audio_url", "", 1)


def test_guide_audio_migration_defines_safe_historical_none_defaults():
    migration = load_migration()
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "audio_status" in source
    assert "none" in source
    assert "narration_text" in source
    assert "audio_object_key" in source
    assert "audio_source_hash" in source
    assert "audio_generation_token" in source
    assert hasattr(migration, "upgrade")
    assert hasattr(migration, "downgrade")
