"""add completed at to exploration plans

Revision ID: e6c5a1f9b2d3
Revises: d2842a9e808b
Create Date: 2026-08-05 21:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "e6c5a1f9b2d3"
down_revision = "d2842a9e808b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "exploration_plans",
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column("exploration_plans", "completed_at")
