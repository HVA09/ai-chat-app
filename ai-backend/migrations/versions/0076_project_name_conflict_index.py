"""Enforce case-insensitive project-name uniqueness per workspace.

Revision ID: 0076_project_name_conflict_index
Revises: 0075_project_preview_artifacts
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0076_project_name_conflict_index"
down_revision: Union[str, None] = "0075_project_preview_artifacts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX uq_workspace_projects_workspace_lower_name
        ON workspace_projects (workspace_id, lower(name))
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS uq_workspace_projects_workspace_lower_name"
    )
