"""Add persistent instructions to workspace projects.

Revision ID: 0055_project_instructions
Revises: 0054_project_knowledge_files
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0055_project_instructions"
down_revision: Union[str, None] = "0054_project_knowledge_files"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workspace_projects",
        sa.Column("instructions", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workspace_projects", "instructions")
