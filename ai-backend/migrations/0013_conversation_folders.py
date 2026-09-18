"""إضافة مجلدات لتنظيم المحادثات.

Revision ID: 0013_conversation_folders
Revises: 0012_conversation_archived
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0013_conversation_folders"
down_revision: Union[str, None] = "0012_conversation_archived"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_folders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_conversation_folders_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id",
            "name",
            name="uq_conversation_folders_user_name",
        ),
    )
    op.create_index(
        "ix_conversation_folders_user_id",
        "conversation_folders",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_folders_user_id_created_at",
        "conversation_folders",
        ["user_id", "created_at"],
        unique=False,
    )
    op.add_column(
        "conversations",
        sa.Column("folder_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_conversations_folder_id",
        "conversations",
        ["folder_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_conversations_folder_id_conversation_folders",
        "conversations",
        "conversation_folders",
        ["folder_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_conversations_folder_id_conversation_folders",
        "conversations",
        type_="foreignkey",
    )
    op.drop_index("ix_conversations_folder_id", table_name="conversations")
    op.drop_column("conversations", "folder_id")
    op.drop_index(
        "ix_conversation_folders_user_id_created_at",
        table_name="conversation_folders",
    )
    op.drop_index("ix_conversation_folders_user_id", table_name="conversation_folders")
    op.drop_table("conversation_folders")
