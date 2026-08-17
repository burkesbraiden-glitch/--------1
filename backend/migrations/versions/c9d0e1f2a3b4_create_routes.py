"""create routes

Revision ID: c9d0e1f2a3b4
Revises: a7b8c9d0e1f2
Create Date: 2026-08-17 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c9d0e1f2a3b4"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "routes",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'ready')", name="route_status_allowed"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_routes_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_routes")),
    )
    op.create_index(op.f("ix_routes_user_id"), "routes", ["user_id"], unique=False)
    op.create_index(op.f("ix_routes_city"), "routes", ["city"], unique=False)

    op.create_table(
        "route_days",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("route_id", sa.BigInteger(), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("title", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("day_number > 0", name="route_day_number_positive"),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["routes.id"],
            name=op.f("fk_route_days_route_id_routes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_route_days")),
        sa.UniqueConstraint("route_id", "day_number", name="route_day_number_unique"),
    )
    op.create_index(op.f("ix_route_days_route_id"), "route_days", ["route_id"], unique=False)

    op.create_table(
        "route_stops",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("route_day_id", sa.BigInteger(), nullable=False),
        sa.Column("attraction_id", sa.BigInteger(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("sort_order > 0", name="route_stop_sort_order_positive"),
        sa.ForeignKeyConstraint(
            ["route_day_id"],
            ["route_days.id"],
            name=op.f("fk_route_stops_route_day_id_route_days"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["attraction_id"],
            ["attractions.id"],
            name=op.f("fk_route_stops_attraction_id_attractions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_route_stops")),
        sa.UniqueConstraint("route_day_id", "sort_order", name="route_stop_sort_order_unique"),
    )
    op.create_index(op.f("ix_route_stops_route_day_id"), "route_stops", ["route_day_id"], unique=False)
    op.create_index(op.f("ix_route_stops_attraction_id"), "route_stops", ["attraction_id"], unique=False)


def downgrade():
    op.drop_table("route_stops")
    op.drop_table("route_days")
    op.drop_table("routes")
