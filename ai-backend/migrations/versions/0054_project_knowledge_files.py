"""إضافة ربط الملفات بالمشاريع لتصبح معرفة خاصة بالمشروع.

Revision ID: 0054_project_knowledge_files
Revises: 0053_plan_model_entitlements
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0054_project_knowledge_files"
down_revision: Union[str, None] = "0053_plan_model_entitlements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "file_attachments",
        sa.Column("project_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_file_attachments_project_id",
        "file_attachments",
        ["project_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_file_attachments_project_id_workspace_projects",
        "file_attachments",
        "workspace_projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_file_attachments_project_id_workspace_projects",
        "file_attachments",
        type_="foreignkey",
    )
    op.drop_index("ix_file_attachments_project_id", table_name="file_attachments")
    op.drop_column("file_attachments", "project_id")
