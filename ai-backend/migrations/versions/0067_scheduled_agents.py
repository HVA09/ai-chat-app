"""Add scheduled Agent execution mode and scheduled run/job linkage.

Revision ID: 0067_scheduled_agents
Revises: 0066_agent_jobs
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0067_scheduled_agents"
down_revision: Union[str, None] = "0066_agent_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    execution_mode_enum = sa.Enum(
        "standard",
        "agent",
        name="scheduledtaskexecutionmode",
    )
    execution_mode_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "scheduled_tasks",
        sa.Column(
            "execution_mode",
            execution_mode_enum,
            nullable=False,
            server_default="standard",
        ),
    )
    op.create_index(
        "ix_scheduled_tasks_execution_mode",
        "scheduled_tasks",
        ["execution_mode"],
    )
    op.add_column(
        "scheduled_task_runs",
        sa.Column(
            "agent_job_id",
            sa.Integer(),
            sa.ForeignKey("agent_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_scheduled_task_runs_agent_job_id",
        "scheduled_task_runs",
        ["agent_job_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scheduled_task_runs_agent_job_id",
        table_name="scheduled_task_runs",
    )
    op.drop_column("scheduled_task_runs", "agent_job_id")
    op.drop_index(
        "ix_scheduled_tasks_execution_mode",
        table_name="scheduled_tasks",
    )
    op.drop_column("scheduled_tasks", "execution_mode")
    sa.Enum(
        "standard",
        "agent",
        name="scheduledtaskexecutionmode",
    ).drop(op.get_bind(), checkfirst=True)
