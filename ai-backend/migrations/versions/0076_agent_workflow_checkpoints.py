"""Add persistent Agent workflow steps and checkpoints.

Revision ID: 0076_agent_workflow_checkpoints
Revises: 0075_project_preview_artifacts
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0076_agent_workflow_checkpoints"
down_revision: Union[str, None] = "0075_project_preview_artifacts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_workflow_steps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_job_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="queued", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("result_text", sa.Text(), nullable=True),
        sa.Column("result_sources", sa.JSON(), nullable=True),
        sa.Column("checkpoint", sa.JSON(), nullable=True),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["agent_job_id"],
            ["agent_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "agent_job_id",
            "sequence",
            name="uq_agent_workflow_steps_job_sequence",
        ),
    )
    op.create_index(
        "ix_agent_workflow_steps_agent_job_id",
        "agent_workflow_steps",
        ["agent_job_id"],
    )
    op.create_index(
        "ix_agent_workflow_steps_job_status",
        "agent_workflow_steps",
        ["agent_job_id", "status"],
    )
    op.create_index(
        "ix_agent_workflow_steps_job_sequence",
        "agent_workflow_steps",
        ["agent_job_id", "sequence"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_workflow_steps_job_sequence",
        table_name="agent_workflow_steps",
    )
    op.drop_index(
        "ix_agent_workflow_steps_job_status",
        table_name="agent_workflow_steps",
    )
    op.drop_index(
        "ix_agent_workflow_steps_agent_job_id",
        table_name="agent_workflow_steps",
    )
    op.drop_table("agent_workflow_steps")
