"""E8 versioned prompts and assistant knowledge snapshots.

Revision ID: 0071_e8_versioned_prompts
Revises: 0070_enterprise_rbac
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0071_e8_versioned_prompts"
down_revision: Union[str, None] = "0070_enterprise_rbac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "saved_prompt_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "prompt_id",
            sa.Integer(),
            sa.ForeignKey("saved_prompts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "prompt_id",
            "version",
            name="uq_saved_prompt_versions_prompt_version",
        ),
    )
    op.create_index(
        "ix_saved_prompt_versions_prompt_id",
        "saved_prompt_versions",
        ["prompt_id"],
    )
    op.create_index(
        "ix_saved_prompt_versions_prompt_id_created_at",
        "saved_prompt_versions",
        ["prompt_id", "created_at"],
    )

    op.add_column(
        "assistant_versions",
        sa.Column(
            "knowledge_file_ids",
            sa.JSON(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("assistant_versions", "knowledge_file_ids")
    op.drop_index(
        "ix_saved_prompt_versions_prompt_id_created_at",
        table_name="saved_prompt_versions",
    )
    op.drop_index(
        "ix_saved_prompt_versions_prompt_id",
        table_name="saved_prompt_versions",
    )
    op.drop_table("saved_prompt_versions")
