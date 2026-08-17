"""create attractions and guides

Revision ID: a7b8c9d0e1f2
Revises: f6a52a1b2d4
Create Date: 2026-08-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "a7b8c9d0e1f2"
down_revision = "f6a52a1b2d4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "attractions",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("district", sa.String(length=80), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("recommended_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("cover_image", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attractions")),
        sa.UniqueConstraint("city", "name", name="city_name_unique"),
    )
    op.create_index(op.f("ix_attractions_name"), "attractions", ["name"], unique=False)
    op.create_index(op.f("ix_attractions_city"), "attractions", ["city"], unique=False)
    op.create_index(op.f("ix_attractions_is_active"), "attractions", ["is_active"], unique=False)

    op.create_table(
        "attraction_guides",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("attraction_id", sa.BigInteger(), nullable=False),
        sa.Column("overview", sa.Text(), nullable=False),
        sa.Column("highlights", sa.JSON(), nullable=False),
        sa.Column("visit_tips", sa.JSON(), nullable=False),
        sa.Column("family_tips", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["attraction_id"],
            ["attractions.id"],
            name=op.f("fk_attraction_guides_attraction_id_attractions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attraction_guides")),
    )
    op.create_index(
        op.f("ix_attraction_guides_attraction_id"),
        "attraction_guides",
        ["attraction_id"],
        unique=True,
    )


def downgrade():
    op.drop_table("attraction_guides")
    op.drop_table("attractions")
