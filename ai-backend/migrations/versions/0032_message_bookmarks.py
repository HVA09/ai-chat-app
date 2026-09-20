"""إضافة إمكانية حفظ الرسائل في المفضلة.

Revision ID: 0032_message_bookmarks
Revises: 0031_saved_prompts
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0032_message_bookmarks"
down_revision: Union[str, None] = "0031_saved_prompts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("is_bookmarked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ix_messages_is_bookmarked",
        "messages",
        ["is_bookmarked"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_messages_is_bookmarked", table_name="messages")
    op.drop_column("messages", "is_bookmarked")
