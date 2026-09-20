"""ربط الملفات بالمحادثات.

Revision ID: 0014_conversation_file_links
Revises: 0013_conversation_folders
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0014_conversation_file_links"
down_revision: Union[str, None] = "0013_conversation_folders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_file_links",
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_conversation_file_links_conversation_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["file_attachments.id"],
            name="fk_conversation_file_links_file_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("conversation_id", "file_id"),
    )
    op.create_index(
        "ix_conversation_file_links_file_id",
        "conversation_file_links",
        ["file_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conversation_file_links_file_id",
        table_name="conversation_file_links",
    )
    op.drop_table("conversation_file_links")
