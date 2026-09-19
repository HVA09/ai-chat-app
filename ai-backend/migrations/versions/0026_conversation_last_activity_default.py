"""إضافة default لوقت آخر نشاط للمحادثات.

Revision ID: 0026_activity_default
Revises: 0025_conversation_last_activity
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0026_activity_default"
down_revision: Union[str, None] = "0025_conversation_last_activity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "conversations",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )


def downgrade() -> None:
    op.alter_column(
        "conversations",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        server_default=None,
    )
