"""إضافة حالة الأرشفة للمحادثات

Revision ID: 0012_conversation_archived
Revises: 0011_conversation_pinned
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012_conversation_archived"
down_revision: Union[str, None] = "0011_conversation_pinned"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ix_conversations_is_archived",
        "conversations",
        ["is_archived"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_is_archived", table_name="conversations")
    op.drop_column("conversations", "is_archived")
