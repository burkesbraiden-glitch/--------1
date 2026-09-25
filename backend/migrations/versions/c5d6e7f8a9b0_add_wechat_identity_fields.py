"""add WeChat identity fields

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-09-24
"""

from alembic import op
import sqlalchemy as sa


revision = "c5d6e7f8a9b0"
down_revision = "b4c5d6e7f8a9"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column("nickname", existing_type=sa.String(length=50), nullable=True)
        batch_op.add_column(sa.Column("wechat_unionid", sa.String(length=128), nullable=True))
        batch_op.create_index("ix_users_wechat_unionid", ["wechat_unionid"], unique=True)


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index("ix_users_wechat_unionid")
        batch_op.drop_column("wechat_unionid")
        batch_op.alter_column("nickname", existing_type=sa.String(length=50), nullable=False)
