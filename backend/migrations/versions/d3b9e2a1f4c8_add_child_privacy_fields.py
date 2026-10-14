"""add child privacy fields

Revision ID: d3b9e2a1f4c8
Revises: c5d6e7f8a9b0
"""

from alembic import op
import sqlalchemy as sa


revision = "d3b9e2a1f4c8"
down_revision = "c5d6e7f8a9b0"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("children", schema=None) as batch_op:
        batch_op.add_column(sa.Column("avatar_preset", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("guardian_consent_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("guardian_consent_version", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("guardian_consent_source", sa.String(length=32), nullable=True))


def downgrade():
    with op.batch_alter_table("children", schema=None) as batch_op:
        batch_op.drop_column("guardian_consent_source")
        batch_op.drop_column("guardian_consent_version")
        batch_op.drop_column("guardian_consent_at")
        batch_op.drop_column("avatar_preset")
