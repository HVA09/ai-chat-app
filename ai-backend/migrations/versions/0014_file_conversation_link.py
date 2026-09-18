"""ربط الملفات بالمحادثات اختيارياً.

Revision ID: 0014_file_conversation_link
Revises: 0013_conversation_folders
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0014_file_conversation_link"
down_revision: Union[str, None] = "0013_conversation_folders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "file_attachments",
        sa.Column("conversation_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_file_attachments_conversation_id",
        "file_attachments",
        ["conversation_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_file_attachments_conversation_id_conversations",
        "file_attachments",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_file_attachments_conversation_id_conversations",
        "file_attachments",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_file_attachments_conversation_id",
        table_name="file_attachments",
    )
    op.drop_column("file_attachments", "conversation_id")
