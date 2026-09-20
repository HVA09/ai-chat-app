"""إضافة نطاق مساحة العمل لمجلدات المحادثات.

Revision ID: 0041_workspace_scoped_folders
Revises: 0040_api_key_controls
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0041_workspace_scoped_folders"
down_revision: Union[str, None] = "0040_api_key_controls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversation_folders",
        sa.Column("workspace_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_conversation_folders_workspace_id",
        "conversation_folders",
        ["workspace_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_conversation_folders_workspace_id_workspaces",
        "conversation_folders",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "uq_conversation_folders_user_name",
        "conversation_folders",
        type_="unique",
    )
    op.create_index(
        "uq_conversation_folders_user_personal_name",
        "conversation_folders",
        ["user_id", "name"],
        unique=True,
        postgresql_where=sa.text("workspace_id IS NULL"),
    )
    op.create_index(
        "uq_conversation_folders_workspace_name",
        "conversation_folders",
        ["workspace_id", "name"],
        unique=True,
        postgresql_where=sa.text("workspace_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_conversation_folders_workspace_name",
        table_name="conversation_folders",
    )
    op.drop_index(
        "uq_conversation_folders_user_personal_name",
        table_name="conversation_folders",
    )
    op.create_unique_constraint(
        "uq_conversation_folders_user_name",
        "conversation_folders",
        ["user_id", "name"],
    )
    op.drop_constraint(
        "fk_conversation_folders_workspace_id_workspaces",
        "conversation_folders",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_conversation_folders_workspace_id",
        table_name="conversation_folders",
    )
    op.drop_column("conversation_folders", "workspace_id")
