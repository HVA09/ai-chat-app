"""تخزين النص المستخرج من الملفات القابلة للقراءة.

Revision ID: 0015_file_extracted_text
Revises: 0014_conversation_file_links
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0015_file_extracted_text"
down_revision: Union[str, None] = "0014_conversation_file_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "file_attachments",
        sa.Column("extracted_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("file_attachments", "extracted_text")
