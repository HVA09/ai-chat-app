"""مشاركة المحادثات للقراءة فقط داخل مساحة العمل.

Revision ID: 0034_conversation_workspace_shares
Revises: 0033_merge_migration_heads
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0034_conversation_workspace_shares"
down_revision: Union[str, None] = "0033_merge_migration_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_workspace_shares",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("shared_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_conversation_workspace_shares_conversation_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_conversation_workspace_shares_workspace_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["shared_by_user_id"],
            ["users.id"],
            name="fk_conversation_workspace_shares_shared_by_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "conversation_id",
            "workspace_id",
            name="uq_conversation_workspace_share",
        ),
    )
    op.create_index(
        "ix_conversation_workspace_shares_conversation_id",
        "conversation_workspace_shares",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_workspace_shares_workspace_id",
        "conversation_workspace_shares",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_workspace_shares_shared_by_user_id",
        "conversation_workspace_shares",
        ["shared_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_workspace_shares_workspace_created",
        "conversation_workspace_shares",
        ["workspace_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conversation_workspace_shares_workspace_created",
        table_name="conversation_workspace_shares",
    )
    op.drop_index(
        "ix_conversation_workspace_shares_shared_by_user_id",
        table_name="conversation_workspace_shares",
    )
    op.drop_index(
        "ix_conversation_workspace_shares_workspace_id",
        table_name="conversation_workspace_shares",
    )
    op.drop_index(
        "ix_conversation_workspace_shares_conversation_id",
        table_name="conversation_workspace_shares",
    )
    op.drop_table("conversation_workspace_shares")
