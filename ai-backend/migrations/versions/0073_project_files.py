"""Add persistent project source files.

Revision ID: 0073_project_files
Revises: 0072_platform_asset_versioning
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0073_project_files"
down_revision: Union[str, None] = "0072_platform_asset_versioning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("workspace_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "project_id",
            "path",
            name="uq_project_files_project_path",
        ),
    )
    op.create_index(
        "ix_project_files_project_id",
        "project_files",
        ["project_id"],
    )
    op.create_index(
        "ix_project_files_project_id_updated_at",
        "project_files",
        ["project_id", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_files_project_id_updated_at",
        table_name="project_files",
    )
    op.drop_index("ix_project_files_project_id", table_name="project_files")
    op.drop_table("project_files")
