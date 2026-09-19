"""إضافة سلة محذوفات للمحادثات.

Revision ID: 0027_conversation_deleted_at
Revises: 0026_conversation_last_activity_default
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0027_conversation_deleted_at"
down_revision: Union[str, None] = "0026_conversation_last_activity_default"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_conversations_user_id_deleted_at",
        "conversations",
        ["user_id", "deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conversations_user_id_deleted_at",
        table_name="conversations",
    )
    op.drop_column("conversations", "deleted_at")
