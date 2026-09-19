"""إضافة ملخص دائم للمحادثات.

Revision ID: 0030_conversation_summary
Revises: 0029_user_memories
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0030_conversation_summary"
down_revision: Union[str, None] = "0029_user_memories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("summary", sa.Text(), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("summary_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversations", "summary_updated_at")
    op.drop_column("conversations", "summary")
