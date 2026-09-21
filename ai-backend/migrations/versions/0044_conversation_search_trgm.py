"""تحسين أداء بحث المحادثات باستخدام pg_trgm.

Revision ID: 0044_conversation_search_trgm
Revises: 0043_conversation_branch_links
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0044_conversation_search_trgm"
down_revision: Union[str, None] = "0043_conversation_branch_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_conversations_title_trgm
        ON conversations USING gin (title gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_messages_content_trgm
        ON messages USING gin (content gin_trgm_ops)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_messages_content_trgm")
    op.execute("DROP INDEX IF EXISTS ix_conversations_title_trgm")
