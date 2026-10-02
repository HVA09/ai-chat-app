"""Add project-level collaboration memberships.

Revision ID: 0074_project_collaboration
Revises: 0073_project_files
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0074_project_collaboration"
down_revision: Union[str, None] = "0073_project_files"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    role_enum = sa.Enum(
        "viewer",
        "editor",
        "manager",
        name="projectmemberrole",
    )

    op.create_table(
        "project_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("workspace_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            role_enum,
            nullable=False,
            server_default="viewer",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "project_id",
            "user_id",
            name="uq_project_members_project_user",
        ),
    )
    op.create_index(
        "ix_project_members_user_id",
        "project_members",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_project_members_user_id", table_name="project_members")
    op.drop_table("project_members")
    sa.Enum(
        "viewer",
        "editor",
        "manager",
        name="projectmemberrole",
    ).drop(op.get_bind(), checkfirst=True)
