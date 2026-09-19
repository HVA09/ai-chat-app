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
    # The workspacerole enum is created/reused by migration 0020.
    # Use raw SQL here so SQLAlchemy cannot emit an implicit CREATE TYPE again.
    op.execute(
        """CREATE TABLE workspace_invitations (
            id INTEGER PRIMARY KEY,
            workspace_id INTEGER NOT NULL,
            invited_by_user_id INTEGER NOT NULL,
            invited_user_id INTEGER NOT NULL,
            email VARCHAR(255) NOT NULL,
            role workspacerole NOT NULL DEFAULT 'member',
            token_hash VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ NOT NULL,
            accepted_at TIMESTAMPTZ NULL,
            revoked_at TIMESTAMPTZ NULL,
            CONSTRAINT fk_workspace_invitations_workspace_id_workspaces
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
            CONSTRAINT fk_workspace_invitations_invited_by_user_id_users
                FOREIGN KEY (invited_by_user_id) REFERENCES users(id) ON DELETE CASCADE,
            CONSTRAINT fk_workspace_invitations_invited_user_id_users
                FOREIGN KEY (invited_user_id) REFERENCES users(id) ON DELETE CASCADE,
            CONSTRAINT uq_workspace_invitations_token_hash UNIQUE (token_hash)
        )"""
    )
    op.create_index("ix_workspace_invitations_workspace_email", "workspace_invitations", ["workspace_id", "email"], unique=False)
    op.create_index("ix_workspace_invitations_invited_user_id", "workspace_invitations", ["invited_user_id"], unique=False)
    op.create_index("ix_workspace_invitations_expires_at", "workspace_invitations", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workspace_invitations_expires_at", table_name="workspace_invitations")
    op.drop_index("ix_workspace_invitations_invited_user_id", table_name="workspace_invitations")
    op.drop_index("ix_workspace_invitations_workspace_email", table_name="workspace_invitations")
    op.drop_table("workspace_invitations")
