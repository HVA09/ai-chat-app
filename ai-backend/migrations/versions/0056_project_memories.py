"""إضافة الذاكرة المشتركة الخاصة بمشاريع مساحة العمل.

Revision ID: 0056_project_memories
Revises: 0054_project_knowledge_files
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0056_project_memories"
down_revision: Union[str, None] = "0055_project_instructions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_memories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["workspace_projects.id"],
            name="fk_project_memories_project_id_workspace_projects",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_project_memories_created_by_user_id_users",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_project_memories_project_id",
        "project_memories",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_memories_project_id_updated_at",
        "project_memories",
        ["project_id", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_project_memories_created_by_user_id",
        "project_memories",
        ["created_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_memories_created_by_user_id",
        table_name="project_memories",
    )
    op.drop_index(
        "ix_project_memories_project_id_updated_at",
        table_name="project_memories",
    )
    op.drop_index("ix_project_memories_project_id", table_name="project_memories")
    op.drop_table("project_memories")
