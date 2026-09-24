"""add phone verification codes

Revision ID: b4c5d6e7f8a9
Revises: a1b2c3d4e5f6
Create Date: 2026-09-24
"""

from alembic import op
import sqlalchemy as sa


revision = "b4c5d6e7f8a9"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "phone_verification_codes",
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("failed_attempts >= 0", name="ck_phone_verification_codes_failed_attempts_nonnegative"),
        sa.PrimaryKeyConstraint("phone"),
    )


def downgrade():
    op.drop_table("phone_verification_codes")
