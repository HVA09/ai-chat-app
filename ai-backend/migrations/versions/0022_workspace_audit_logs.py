"""ربط سجل التدقيق بمساحات العمل.

Revision ID: 0022_workspace_audit_logs
Revises: 0021_workspace_invitations
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0022_workspace_audit_logs"
down_revision: Union[str, None] = "0021_workspace_invitations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "audit_logs",
        sa.Column("workspace_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_audit_logs_workspace_id_created_at",
        "audit_logs",
        ["workspace_id", "created_at"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_audit_logs_workspace_id_workspaces",
        "audit_logs",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_audit_logs_workspace_id_workspaces",
        "audit_logs",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_audit_logs_workspace_id_created_at",
        table_name="audit_logs",
    )
    op.drop_column("audit_logs", "workspace_id")
