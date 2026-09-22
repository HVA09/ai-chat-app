"""إضافة تعليقات التعاون على المحادثات المشتركة.

Revision ID: 0060_conversation_comments
Revises: 0059_assistant_versions
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0060_conversation_comments"
down_revision: Union[str, None] = "0059_assistant_versions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_conversation_comments_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_conversation_comments_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            name="fk_conversation_comments_message_id_messages",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_conversation_comments_conversation_id",
        "conversation_comments",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_comments_user_id",
        "conversation_comments",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_comments_conversation_created_at",
        "conversation_comments",
        ["conversation_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_comments_message_id",
        "conversation_comments",
        ["message_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_comments_message_id", table_name="conversation_comments")
    op.drop_index(
        "ix_conversation_comments_conversation_created_at",
        table_name="conversation_comments",
    )
    op.drop_index("ix_conversation_comments_user_id", table_name="conversation_comments")
    op.drop_index(
        "ix_conversation_comments_conversation_id",
        table_name="conversation_comments",
    )
    op.drop_table("conversation_comments")
