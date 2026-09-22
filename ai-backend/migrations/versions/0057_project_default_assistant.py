"""إضافة المساعد الافتراضي للمشروع.

Revision ID: 0057_project_default_assistant
Revises: 0056_project_memories
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0057_project_default_assistant"
down_revision: Union[str, None] = "0056_project_memories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workspace_projects",
        sa.Column("assistant_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_workspace_projects_assistant_id",
        "workspace_projects",
        ["assistant_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_workspace_projects_assistant_id_assistants",
        "workspace_projects",
        "assistants",
        ["assistant_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_workspace_projects_assistant_id_assistants",
        "workspace_projects",
        type_="foreignkey",
    )
    op.drop_index("ix_workspace_projects_assistant_id", table_name="workspace_projects")
    op.drop_column("workspace_projects", "assistant_id")
