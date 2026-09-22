"""إضافة ملفات معرفة دائمة للمعاونين.

Revision ID: 0058_assistant_knowledge_files
Revises: 0057_project_default_assistant
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0058_assistant_knowledge_files"
down_revision: Union[str, None] = "0057_project_default_assistant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assistant_file_links",
        sa.Column("assistant_id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assistant_id"],
            ["assistants.id"],
            name="fk_assistant_file_links_assistant_id_assistants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["file_attachments.id"],
            name="fk_assistant_file_links_file_id_file_attachments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("assistant_id", "file_id"),
    )


def downgrade() -> None:
    op.drop_table("assistant_file_links")
