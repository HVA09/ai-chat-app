"""إضافة وسوم متعددة للمحادثات.

Revision ID: 0026_conversation_tags
Revises: 0025_conversation_last_activity
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0026_conversation_tags"
down_revision: Union[str, None] = "0025_conversation_last_activity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False, server_default="#64748B"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_conversation_tags_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id",
            "name",
            name="uq_conversation_tags_user_name",
        ),
    )
    op.create_index(
        "ix_conversation_tags_user_id",
        "conversation_tags",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_tags_user_id_created_at",
        "conversation_tags",
        ["user_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "conversation_tag_links",
        sa.Column("conversation_id", sa.Integer(), primary_key=True),
        sa.Column("tag_id", sa.Integer(), primary_key=True),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_conversation_tag_links_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["conversation_tags.id"],
            name="fk_conversation_tag_links_tag_id_conversation_tags",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_conversation_tag_links_tag_id",
        "conversation_tag_links",
        ["tag_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_tag_links_tag_id", table_name="conversation_tag_links")
    op.drop_table("conversation_tag_links")
    op.drop_index(
        "ix_conversation_tags_user_id_created_at",
        table_name="conversation_tags",
    )
    op.drop_index("ix_conversation_tags_user_id", table_name="conversation_tags")
    op.drop_table("conversation_tags")
