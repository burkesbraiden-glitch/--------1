import importlib.util
from pathlib import Path

import sqlalchemy as sa


MIGRATION_PATH = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "c9d0e1f2a3b4_create_routes.py"


def load_migration():
    spec = importlib.util.spec_from_file_location("route_migration", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _collect_upgrade_schema(monkeypatch):
    migration = load_migration()
    tables = []
    indexes = []

    monkeypatch.setattr(migration.op, "f", lambda name: name)
    monkeypatch.setattr(
        migration.op,
        "create_table",
        lambda name, *args, **kwargs: tables.append((name, args, kwargs)),
    )
    monkeypatch.setattr(
        migration.op,
        "create_index",
        lambda name, table, columns, **kwargs: indexes.append((name, table, columns, kwargs)),
    )
    migration.upgrade()
    return tables, indexes


def _table_by_name(tables, name):
    return next(args for table_name, args, _kwargs in tables if table_name == name)


def _columns(args):
    return {item.name: item for item in args if isinstance(item, sa.Column)}


def _foreign_keys(args):
    return [item for item in args if isinstance(item, sa.ForeignKeyConstraint)]


def _unique_columns(args):
    return {
        tuple(
            column.name if hasattr(column, "name") else column
            for column in (constraint.columns or constraint._pending_colargs)
        )
        for constraint in args
        if isinstance(constraint, sa.UniqueConstraint)
    }


def _check_sql(args):
    return {
        str(constraint.sqltext)
        for constraint in args
        if isinstance(constraint, sa.CheckConstraint)
    }


def test_route_migration_has_expected_parent_revision():
    migration = load_migration()

    assert migration.revision == "c9d0e1f2a3b4"
    assert migration.down_revision == "a7b8c9d0e1f2"


def test_route_migration_creates_only_route_tables_with_expected_columns_constraints_and_indexes(monkeypatch):
    tables, indexes = _collect_upgrade_schema(monkeypatch)

    assert [name for name, _args, _kwargs in tables] == ["routes", "route_days", "route_stops"]
    routes = _table_by_name(tables, "routes")
    route_days = _table_by_name(tables, "route_days")
    route_stops = _table_by_name(tables, "route_stops")

    route_columns = _columns(routes)
    assert set(route_columns) == {"id", "user_id", "title", "city", "start_date", "end_date", "status", "created_at", "updated_at"}
    assert isinstance(route_columns["start_date"].type, sa.Date)
    assert isinstance(route_columns["end_date"].type, sa.Date)
    assert route_columns["status"].server_default is not None
    assert "status IN ('draft', 'ready')" in _check_sql(routes)
    assert _foreign_keys(routes)[0].ondelete == "CASCADE"
    assert _foreign_keys(routes)[0].elements[0].target_fullname == "users.id"

    day_columns = _columns(route_days)
    assert set(day_columns) == {"id", "route_id", "day_number", "date", "title", "created_at", "updated_at"}
    assert isinstance(day_columns["date"].type, sa.Date)
    assert ("route_id", "day_number") in _unique_columns(route_days)
    assert "day_number > 0" in _check_sql(route_days)
    assert _foreign_keys(route_days)[0].ondelete == "CASCADE"
    assert _foreign_keys(route_days)[0].elements[0].target_fullname == "routes.id"

    stop_columns = _columns(route_stops)
    assert set(stop_columns) == {"id", "route_day_id", "attraction_id", "sort_order", "note", "created_at", "updated_at"}
    assert ("route_day_id", "sort_order") in _unique_columns(route_stops)
    assert "sort_order > 0" in _check_sql(route_stops)
    assert {foreign_key.elements[0].target_fullname: foreign_key.ondelete for foreign_key in _foreign_keys(route_stops)} == {
        "route_days.id": "CASCADE",
        "attractions.id": "RESTRICT",
    }

    assert [(table, columns) for _name, table, columns, _kwargs in indexes] == [
        ("routes", ["user_id"]),
        ("routes", ["city"]),
        ("route_days", ["route_id"]),
        ("route_stops", ["route_day_id"]),
        ("route_stops", ["attraction_id"]),
    ]


def test_route_migration_downgrade_drops_only_route_tables_in_reverse_order(monkeypatch):
    migration = load_migration()
    tables = []
    monkeypatch.setattr(migration.op, "drop_table", tables.append)

    migration.downgrade()

    assert tables == ["route_stops", "route_days", "routes"]
