"""add guide audio domain

Revision ID: f8e7d6c5b4a3
Revises: ea8f05d3f3af
"""
from alembic import op
import sqlalchemy as sa


revision = "f8e7d6c5b4a3"
down_revision = "ea8f05d3f3af"
branch_labels = None
depends_on = None


def upgrade():
    # audio_url is intentionally retained as an untrusted legacy field. Historical
    # rows receive audio_status=none and are never promoted to ready by migration.
    with op.batch_alter_table("guide_cards", schema=None) as batch_op:
        batch_op.add_column(sa.Column("narration_text", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("guide_version", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("audio_status", sa.String(length=24), nullable=False, server_default="none"))
        batch_op.add_column(sa.Column("audio_object_key", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("audio_source_hash", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("audio_generation_token", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("audio_duration_sec", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("audio_generated_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("audio_error_code", sa.String(length=64), nullable=True))
        batch_op.create_check_constraint(
            "ck_guide_cards_audio_status_allowed",
            "audio_status IN ('none', 'pending', 'generating', 'ready', 'failed')",
        )


def downgrade():
    with op.batch_alter_table("guide_cards", schema=None) as batch_op:
        batch_op.drop_constraint("ck_guide_cards_audio_status_allowed", type_="check")
        batch_op.drop_column("audio_error_code")
        batch_op.drop_column("audio_generated_at")
        batch_op.drop_column("audio_duration_sec")
        batch_op.drop_column("audio_generation_token")
        batch_op.drop_column("audio_source_hash")
        batch_op.drop_column("audio_object_key")
        batch_op.drop_column("audio_status")
        batch_op.drop_column("guide_version")
        batch_op.drop_column("narration_text")
