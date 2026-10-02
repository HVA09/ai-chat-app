"""Add AgentJob verification and retry checkpoints.

Revision ID: 0078_agent_job_verification_retry
Revises: 0077_merge_f4_f5_heads
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0078_agent_job_verification_retry"
down_revision: Union[str, None] = "0077_merge_f4_f5_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agent_jobs",
        sa.Column(
            "workflow_phase",
            sa.String(length=20),
            nullable=False,
            server_default="queued",
        ),
    )
    op.add_column(
        "agent_jobs",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "agent_jobs",
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="2"),
    )
    op.add_column(
        "agent_jobs",
        sa.Column("checkpoint", sa.JSON(), nullable=True),
    )
    op.add_column(
        "agent_jobs",
        sa.Column("checkpoint_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_agent_jobs_workflow_phase_created_at",
        "agent_jobs",
        ["workflow_phase", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_jobs_workflow_phase_created_at",
        table_name="agent_jobs",
    )
    op.drop_column("agent_jobs", "checkpoint_at")
    op.drop_column("agent_jobs", "checkpoint")
    op.drop_column("agent_jobs", "max_retries")
    op.drop_column("agent_jobs", "retry_count")
    op.drop_column("agent_jobs", "workflow_phase")
