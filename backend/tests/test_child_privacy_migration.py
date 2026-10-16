import importlib.util
from contextlib import contextmanager
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "d3b9e2a1f4c8_add_child_privacy_fields.py"
)


def load_migration():
    spec = importlib.util.spec_from_file_location("child_privacy_migration", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RecordingBatch:
    def __init__(self, calls):
        self.calls = calls

    def add_column(self, column):
        self.calls.append(("add", column.name, column.type, column.nullable))

    def drop_column(self, name):
        self.calls.append(("drop", name))


class RecordingOp:
    def __init__(self):
        self.tables = []
        self.calls = []

    @contextmanager
    def batch_alter_table(self, table_name, schema=None):
        self.tables.append((table_name, schema))
        yield RecordingBatch(self.calls)


def test_child_privacy_migration_is_minimal_additive_and_reversible(monkeypatch):
    migration = load_migration()
    recorder = RecordingOp()
    monkeypatch.setattr(migration, "op", recorder)

    migration.upgrade()
    migration.downgrade()

    assert migration.revision == "d3b9e2a1f4c8"
    assert migration.down_revision == "c5d6e7f8a9b0"
    assert recorder.tables == [("children", None), ("children", None)]
    added_columns = recorder.calls[:4]
    assert [(operation, name, nullable) for operation, name, _type, nullable in added_columns] == [
        ("add", "avatar_preset", True),
        ("add", "guardian_consent_at", True),
        ("add", "guardian_consent_version", True),
        ("add", "guardian_consent_source", True),
    ]
    assert [(type(column_type).__name__, getattr(column_type, "length", None)) for _operation, _name, column_type, _nullable in added_columns] == [
        ("String", 64),
        ("DateTime", None),
        ("String", 16),
        ("String", 32),
    ]
    assert recorder.calls[4:] == [
        ("drop", "guardian_consent_source"),
        ("drop", "guardian_consent_version"),
        ("drop", "guardian_consent_at"),
        ("drop", "avatar_preset"),
    ]


def test_child_privacy_migration_never_backfills_or_drops_existing_child_data():
    source = MIGRATION_PATH.read_text(encoding="utf-8")
    upgrade_source = source.split("def downgrade", 1)[0]

    assert "children" in source
    assert "server_default" not in upgrade_source
    assert "UPDATE" not in upgrade_source
    assert "drop_column" not in upgrade_source


def test_child_privacy_migration_upgrades_and_downgrades_a_temporary_sqlite_database(monkeypatch, tmp_path):
    migration = load_migration()
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'child-privacy.sqlite'}")
    metadata = sa.MetaData()
    children = sa.Table(
        "children",
        metadata,
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("age", sa.SmallInteger(), nullable=False),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(children.insert().values(id=1, name="历史儿童", age=7))
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.upgrade()
        upgraded_columns = {column["name"]: column for column in sa.inspect(connection).get_columns("children")}
        row = connection.execute(sa.text("SELECT * FROM children WHERE id = 1")).mappings().one()

        assert {"avatar_preset", "guardian_consent_at", "guardian_consent_version", "guardian_consent_source"} <= set(upgraded_columns)
        assert row["avatar_preset"] is None
        assert row["guardian_consent_at"] is None
        assert row["guardian_consent_version"] is None
        assert row["guardian_consent_source"] is None

        migration.downgrade()
        downgraded_columns = {column["name"] for column in sa.inspect(connection).get_columns("children")}
        assert {"avatar_preset", "guardian_consent_at", "guardian_consent_version", "guardian_consent_source"}.isdisjoint(downgraded_columns)
        assert connection.execute(sa.text("SELECT name, age FROM children WHERE id = 1")).one() == ("历史儿童", 7)
