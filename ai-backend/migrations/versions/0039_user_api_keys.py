"""إضافة مفاتيح API الشخصية للمستخدمين.

Revision ID: 0039_user_api_keys
Revises: 0038_workspace_ai_daily_limit
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0039_user_api_keys"
down_revision: Union[str, None] = "0038_workspace_ai_daily_limit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("key_prefix", sa.String(length=32), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_api_keys_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("key_hash", name="uq_api_keys_key_hash"),
    )
    op.create_index(
        "ix_api_keys_user_id",
        "api_keys",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_api_keys_user_id_created_at",
        "api_keys",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_api_keys_user_id_created_at", table_name="api_keys")
    op.drop_index("ix_api_keys_user_id", table_name="api_keys")
    op.drop_table("api_keys")
