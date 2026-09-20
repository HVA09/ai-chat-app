"""مشاركة المساعدين المخصصين مع مساحات العمل.

Revision ID: 0035_assistant_workspace_shares
Revises: 0034_workspace_conv_share
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0035_assistant_workspace_shares"
down_revision: Union[str, None] = "0034_workspace_conv_share"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assistant_workspace_shares",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assistant_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("shared_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assistant_id"],
            ["assistants.id"],
            name="fk_assistant_workspace_shares_assistant_id_assistants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_assistant_workspace_shares_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["shared_by_user_id"],
            ["users.id"],
            name="fk_assistant_workspace_shares_shared_by_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "assistant_id",
            "workspace_id",
            name="uq_assistant_workspace_share",
        ),
    )
    op.create_index(
        "ix_assistant_workspace_shares_assistant_id",
        "assistant_workspace_shares",
        ["assistant_id"],
        unique=False,
    )
    op.create_index(
        "ix_assistant_workspace_shares_workspace_id",
        "assistant_workspace_shares",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_assistant_workspace_shares_shared_by_user_id",
        "assistant_workspace_shares",
        ["shared_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_assistant_workspace_shares_workspace_created",
        "assistant_workspace_shares",
        ["workspace_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assistant_workspace_shares_workspace_created",
        table_name="assistant_workspace_shares",
    )
    op.drop_index(
        "ix_assistant_workspace_shares_shared_by_user_id",
        table_name="assistant_workspace_shares",
    )
    op.drop_index(
        "ix_assistant_workspace_shares_workspace_id",
        table_name="assistant_workspace_shares",
    )
    op.drop_index(
        "ix_assistant_workspace_shares_assistant_id",
        table_name="assistant_workspace_shares",
    )
    op.drop_table("assistant_workspace_shares")
