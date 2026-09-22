"""إضافة سجل نسخ إعدادات المساعدين.

Revision ID: 0059_assistant_versions
Revises: 0058_assistant_knowledge_files
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0059_assistant_versions"
down_revision: Union[str, None] = "0058_assistant_knowledge_files"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assistant_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assistant_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assistant_id"],
            ["assistants.id"],
            name="fk_assistant_versions_assistant_id_assistants",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "assistant_id",
            "version",
            name="uq_assistant_versions_assistant_version",
        ),
    )
    op.create_index(
        "ix_assistant_versions_assistant_id",
        "assistant_versions",
        ["assistant_id"],
        unique=False,
    )
    op.create_index(
        "ix_assistant_versions_assistant_id_created_at",
        "assistant_versions",
        ["assistant_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assistant_versions_assistant_id_created_at",
        table_name="assistant_versions",
    )
    op.drop_index("ix_assistant_versions_assistant_id", table_name="assistant_versions")
    op.drop_table("assistant_versions")
