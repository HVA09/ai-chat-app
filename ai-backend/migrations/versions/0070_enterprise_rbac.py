"""Add enterprise workspace RBAC roles and permissions.

Revision ID: 0070_enterprise_rbac
Revises: 0069_oauth_connectors
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0070_enterprise_rbac"
down_revision: Union[str, None] = "0069_oauth_connectors"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspace_rbac_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "name",
            name="uq_workspace_rbac_roles_workspace_name",
        ),
    )
    op.create_index(
        "ix_workspace_rbac_roles_workspace_id",
        "workspace_rbac_roles",
        ["workspace_id"],
    )

    op.create_table(
        "workspace_rbac_permissions",
        sa.Column(
            "role_id",
            sa.Integer(),
            sa.ForeignKey("workspace_rbac_roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("permission", sa.String(length=100), primary_key=True),
    )
    op.create_index(
        "ix_workspace_rbac_permissions_role_id",
        "workspace_rbac_permissions",
        ["role_id"],
    )

    op.add_column(
        "workspace_members",
        sa.Column(
            "rbac_role_id",
            sa.Integer(),
            sa.ForeignKey(
                "workspace_rbac_roles.id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_workspace_members_rbac_role_id",
        "workspace_members",
        ["rbac_role_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workspace_members_rbac_role_id",
        table_name="workspace_members",
    )
    op.drop_column("workspace_members", "rbac_role_id")

    op.drop_index(
        "ix_workspace_rbac_permissions_role_id",
        table_name="workspace_rbac_permissions",
    )
    op.drop_table("workspace_rbac_permissions")

    op.drop_index(
        "ix_workspace_rbac_roles_workspace_id",
        table_name="workspace_rbac_roles",
    )
    op.drop_table("workspace_rbac_roles")
