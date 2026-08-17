import importlib.util
from pathlib import Path


MIGRATION_PATH = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "a7b8c9d0e1f2_create_attractions_and_guides.py"


def load_migration():
    spec = importlib.util.spec_from_file_location("attraction_migration", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_attraction_migration_has_expected_single_parent_revision():
    migration = load_migration()

    assert migration.revision == "a7b8c9d0e1f2"
    assert migration.down_revision == "f6a52a1b2d4"


def test_attraction_migration_creates_only_new_tables_and_indexes(monkeypatch):
    migration = load_migration()
    tables = []
    indexes = []

    monkeypatch.setattr(migration.op, "f", lambda name: name)
    monkeypatch.setattr(migration.op, "create_table", lambda name, *_args, **_kwargs: tables.append(name))
    monkeypatch.setattr(
        migration.op,
        "create_index",
        lambda name, table, columns, **_kwargs: indexes.append((name, table, columns)),
    )

    migration.upgrade()

    assert tables == ["attractions", "attraction_guides"]
    assert [(table, columns) for _, table, columns in indexes] == [
        ("attractions", ["name"]),
        ("attractions", ["city"]),
        ("attractions", ["is_active"]),
        ("attraction_guides", ["attraction_id"]),
    ]


def test_attraction_migration_downgrade_drops_guide_before_attraction(monkeypatch):
    migration = load_migration()
    tables = []
    monkeypatch.setattr(migration.op, "drop_table", tables.append)

    migration.downgrade()

    assert tables == ["attraction_guides", "attractions"]
