"""إضافة نطاق مساحة العمل لمرفقات الملفات.

Revision ID: 0032_workspace_files
Revises: 0031_saved_prompts
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0032_workspace_files"
down_revision: Union[str, None] = "0031_saved_prompts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "file_attachments",
        sa.Column("workspace_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_file_attachments_workspace_id",
        "file_attachments",
        ["workspace_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_file_attachments_workspace_id_workspaces",
        "file_attachments",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_file_attachments_workspace_id_workspaces",
        "file_attachments",
        type_="foreignkey",
    )
    op.drop_index("ix_file_attachments_workspace_id", table_name="file_attachments")
    op.drop_column("file_attachments", "workspace_id")
