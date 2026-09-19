"""إضافة الذاكرة الدائمة للمستخدم.

Revision ID: 0029_user_memories
Revises: 0028_conversation_tags
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0029_user_memories"
down_revision: Union[str, None] = "0028_conversation_tags"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_memories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_memories_user_id_users",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_user_memories_user_id",
        "user_memories",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_memories_user_id_created_at",
        "user_memories",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_memories_user_id_created_at",
        table_name="user_memories",
    )
    op.drop_index("ix_user_memories_user_id", table_name="user_memories")
    op.drop_table("user_memories")
