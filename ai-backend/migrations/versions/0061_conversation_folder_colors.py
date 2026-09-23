"""إضافة لون اختياري لمجلدات المحادثات.

Revision ID: 0061_conversation_folder_colors
Revises: 0060_conversation_comments
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0061_conversation_folder_colors"
down_revision: Union[str, None] = "0060_conversation_comments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversation_folders",
        sa.Column(
            "color",
            sa.String(length=20),
            nullable=False,
            server_default="slate",
        ),
    )


def downgrade() -> None:
    op.drop_column("conversation_folders", "color")
