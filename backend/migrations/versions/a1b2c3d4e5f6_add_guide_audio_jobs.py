"""add guide audio jobs

Revision ID: a1b2c3d4e5f6
Revises: f8e7d6c5b4a3
Create Date: 2026-09-17
"""

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "f8e7d6c5b4a3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "guide_audio_jobs",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("guide_id", sa.BigInteger(), nullable=False),
        sa.Column("guide_version", sa.Integer(), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("generation_token", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="queued"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("provider_job_id", sa.String(length=255), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'claimed', 'provider_pending', 'completed', 'failed', 'stale')",
            name="ck_guide_audio_jobs_status_allowed",
        ),
        sa.ForeignKeyConstraint(["guide_id"], ["guide_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "guide_id",
            "guide_version",
            "source_hash",
            "generation_token",
            name="uq_guide_audio_jobs_generation",
        ),
    )
    op.create_index(
        "ix_guide_audio_jobs_status_available_id",
        "guide_audio_jobs",
        ["status", "available_at", "id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_guide_audio_jobs_status_available_id", table_name="guide_audio_jobs")
    op.drop_table("guide_audio_jobs")
