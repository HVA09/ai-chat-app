"""إضافة دعوات أعضاء مساحات العمل.

Revision ID: 0021_workspace_invitations
Revises: 0020_workspaces
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0021_workspace_invitations"
down_revision: Union[str, None] = "0020_workspaces"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    workspace_role = sa.Enum(
        "owner", "admin", "member", name="workspacerole", create_type=False
    )
    op.create_table(
        "workspace_invitations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("invited_by_user_id", sa.Integer(), nullable=False),
        sa.Column("invited_user_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", workspace_role, nullable=False, server_default="member"),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name="fk_workspace_invitations_workspace_id_workspaces", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], name="fk_workspace_invitations_invited_by_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_user_id"], ["users.id"], name="fk_workspace_invitations_invited_user_id_users", ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_workspace_invitations_token_hash"),
    )
    op.create_index("ix_workspace_invitations_workspace_email", "workspace_invitations", ["workspace_id", "email"], unique=False)
    op.create_index("ix_workspace_invitations_invited_user_id", "workspace_invitations", ["invited_user_id"], unique=False)
    op.create_index("ix_workspace_invitations_expires_at", "workspace_invitations", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workspace_invitations_expires_at", table_name="workspace_invitations")
    op.drop_index("ix_workspace_invitations_invited_user_id", table_name="workspace_invitations")
    op.drop_index("ix_workspace_invitations_workspace_email", table_name="workspace_invitations")
    op.drop_table("workspace_invitations")
