"""link exploration plans to route stops

Revision ID: ea8f05d3f3af
Revises: c9d0e1f2a3b4
Create Date: 2026-08-18 11:53:35.357508

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ea8f05d3f3af'
down_revision = 'c9d0e1f2a3b4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "exploration_plans",
        sa.Column("route_stop_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "exploration_plans",
        sa.Column("source_snapshot", sa.JSON(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_exploration_plans_route_stop_id_route_stops"),
        "exploration_plans",
        "route_stops",
        ["route_stop_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "route_stop_child_unique",
        "exploration_plans",
        ["route_stop_id", "child_id"],
    )


def downgrade():
    op.drop_constraint(
        op.f("fk_exploration_plans_route_stop_id_route_stops"),
        "exploration_plans",
        type_="foreignkey",
    )
    op.drop_constraint("route_stop_child_unique", "exploration_plans", type_="unique")
    op.drop_column("exploration_plans", "source_snapshot")
    op.drop_column("exploration_plans", "route_stop_id")
