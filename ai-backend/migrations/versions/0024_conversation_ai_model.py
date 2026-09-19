"""إضافة النموذج المختار لكل محادثة.

Revision ID: 0024_conversation_ai_model
Revises: 0023_message_feedback
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0024_conversation_ai_model"
down_revision: Union[str, None] = "0023_message_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("ai_model", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversations", "ai_model")
