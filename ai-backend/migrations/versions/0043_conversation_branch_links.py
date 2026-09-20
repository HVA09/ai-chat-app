"""إضافة روابط أصل/فروع المحادثات.

Revision ID: 0043_conversation_branch_links
Revises: 0042_workspace_projects
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0043_conversation_branch_links"
down_revision: Union[str, None] = "0042_workspace_projects"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("parent_conversation_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("branched_from_message_index", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_conversations_parent_conversation_id",
        "conversations",
        ["parent_conversation_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_conversations_parent_conversation_id_conversations",
        "conversations",
        "conversations",
        ["parent_conversation_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_conversations_parent_conversation_id_conversations",
        "conversations",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_conversations_parent_conversation_id",
        table_name="conversations",
    )
    op.drop_column("conversations", "branched_from_message_index")
    op.drop_column("conversations", "parent_conversation_id")
