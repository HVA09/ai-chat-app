"""Add platform asset versioning and Agent configuration snapshots.

Revision ID: 0072_platform_asset_versioning
Revises: 0071_workspace_cost_controls
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0072_platform_asset_versioning"
down_revision: Union[str, None] = "0071_workspace_cost_controls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assistant_versions",
        sa.Column("knowledge_file_ids", sa.JSON(), nullable=True),
    )
    op.add_column(
        "assistant_versions",
        sa.Column("tool_policy_snapshot", sa.JSON(), nullable=True),
    )

    op.add_column(
        "agent_jobs",
        sa.Column(
            "agent_version",
            sa.String(length=64),
            nullable=False,
            server_default="agent-1",
        ),
    )
    op.add_column(
        "agent_jobs",
        sa.Column("tool_policy_snapshot", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_agent_jobs_agent_version",
        "agent_jobs",
        ["agent_version"],
    )

    op.create_table(
        "saved_prompt_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "saved_prompt_id",
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
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "saved_prompt_id",
            "version",
            name="uq_saved_prompt_versions_prompt_version",
        ),
    )
    op.create_index(
        "ix_saved_prompt_versions_saved_prompt_id",
        "saved_prompt_versions",
        ["saved_prompt_id"],
    )
    op.create_index(
        "ix_saved_prompt_versions_prompt_id_created_at",
        "saved_prompt_versions",
        ["saved_prompt_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_saved_prompt_versions_prompt_id_created_at",
        table_name="saved_prompt_versions",
    )
    op.drop_index(
        "ix_saved_prompt_versions_saved_prompt_id",
        table_name="saved_prompt_versions",
    )
    op.drop_table("saved_prompt_versions")

    op.drop_index("ix_agent_jobs_agent_version", table_name="agent_jobs")
    op.drop_column("agent_jobs", "tool_policy_snapshot")
    op.drop_column("agent_jobs", "agent_version")

    op.drop_column("assistant_versions", "tool_policy_snapshot")
    op.drop_column("assistant_versions", "knowledge_file_ids")
