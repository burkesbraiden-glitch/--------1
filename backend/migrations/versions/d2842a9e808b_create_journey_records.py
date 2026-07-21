"""create journey records

Revision ID: d2842a9e808b
Revises: c795c3738e73
Create Date: 2026-07-16 14:04:05.422392

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd2842a9e808b'
down_revision = 'c795c3738e73'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "journey_records",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("plan_id", sa.BigInteger(), nullable=False),
        sa.Column("custom_title", sa.String(length=120), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("cover_submission_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=24),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column("finalized_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'finalized')",
            name=op.f("ck_journey_records_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["cover_submission_id"],
            ["task_submissions.id"],
            name=op.f("fk_journey_records_cover_submission_id_task_submissions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["exploration_plans.id"],
            name=op.f("fk_journey_records_plan_id_exploration_plans"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journey_records")),
        sa.UniqueConstraint("plan_id", name="plan_journey_record"),
    )
    op.create_index(
        op.f("ix_journey_records_cover_submission_id"),
        "journey_records",
        ["cover_submission_id"],
        unique=False,
    )


def downgrade():
    op.drop_table("journey_records")
