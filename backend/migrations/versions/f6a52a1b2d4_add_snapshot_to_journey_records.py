"""add snapshot to journey records

Revision ID: f6a52a1b2d4
Revises: e6c5a1f9b2d3
Create Date: 2026-08-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f6a52a1b2d4"
down_revision = "e6c5a1f9b2d3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("journey_records", sa.Column("snapshot", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("journey_records", "snapshot")
