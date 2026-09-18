"""إضافة حالة التثبيت للمحادثات

Revision ID: 0011_conversation_pinned
Revises: 0010_webhook_events
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011_conversation_pinned"
down_revision: Union[str, None] = "0010_webhook_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ix_conversations_is_pinned",
        "conversations",
        ["is_pinned"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_is_pinned", table_name="conversations")
    op.drop_column("conversations", "is_pinned")
