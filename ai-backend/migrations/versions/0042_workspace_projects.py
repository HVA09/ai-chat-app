"""إضافة مشاريع لمساحات العمل وتنظيم المحادثات.

Revision ID: 0042_workspace_projects
Revises: 0041_workspace_scoped_folders
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0042_workspace_projects"
down_revision: Union[str, None] = "0041_workspace_scoped_folders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspace_projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_workspace_projects_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="fk_workspace_projects_owner_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "name",
            name="uq_workspace_projects_workspace_name",
        ),
    )
    op.create_index(
        "ix_workspace_projects_workspace_id",
        "workspace_projects",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_workspace_projects_workspace_id_created_at",
        "workspace_projects",
        ["workspace_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_workspace_projects_owner_id",
        "workspace_projects",
        ["owner_id"],
        unique=False,
    )

    op.add_column(
        "conversations",
        sa.Column("project_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_conversations_project_id",
        "conversations",
        ["project_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_conversations_project_id_workspace_projects",
        "conversations",
        "workspace_projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_conversations_project_id_workspace_projects",
        "conversations",
        type_="foreignkey",
    )
    op.drop_index("ix_conversations_project_id", table_name="conversations")
    op.drop_column("conversations", "project_id")

    op.drop_index("ix_workspace_projects_owner_id", table_name="workspace_projects")
    op.drop_index(
        "ix_workspace_projects_workspace_id_created_at",
        table_name="workspace_projects",
    )
    op.drop_index("ix_workspace_projects_workspace_id", table_name="workspace_projects")
    op.drop_table("workspace_projects")
