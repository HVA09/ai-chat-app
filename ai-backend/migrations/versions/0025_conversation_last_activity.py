"""إضافة وقت آخر نشاط للمحادثات.

Revision ID: 0025_conversation_last_activity
Revises: 0024_conversation_ai_model
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0025_conversation_last_activity"
down_revision: Union[str, None] = "0024_conversation_ai_model"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE conversations SET updated_at = created_at WHERE updated_at IS NULL"
    )
    op.alter_column(
        "conversations",
        "updated_at",
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    op.create_index(
        "ix_conversations_user_id_updated_at",
        "conversations",
        ["user_id", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_user_id_updated_at", table_name="conversations")
    op.drop_column("conversations", "updated_at")
