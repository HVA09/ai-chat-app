"""Create persistent long-running Agent Platform jobs.

Revision ID: 0066_agent_jobs
Revises: 0065_object_storage
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0066_agent_jobs"
down_revision: Union[str, None] = "0065_object_storage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column(
            "cancel_requested",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("result_text", sa.Text(), nullable=True),
        sa.Column("result_sources", sa.JSON(), nullable=True),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_jobs_user_id", "agent_jobs", ["user_id"])
    op.create_index("ix_agent_jobs_workspace_id", "agent_jobs", ["workspace_id"])
    op.create_index("ix_agent_jobs_conversation_id", "agent_jobs", ["conversation_id"])
    op.create_index("ix_agent_jobs_status", "agent_jobs", ["status"])
    op.create_index("ix_agent_jobs_cancel_requested", "agent_jobs", ["cancel_requested"])
    op.create_index("ix_agent_jobs_celery_task_id", "agent_jobs", ["celery_task_id"], unique=True)
    op.create_index("ix_agent_jobs_run_id", "agent_jobs", ["run_id"])
    op.create_index(
        "ix_agent_jobs_user_created_at",
        "agent_jobs",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_agent_jobs_workspace_created_at",
        "agent_jobs",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_agent_jobs_status_created_at",
        "agent_jobs",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_jobs_status_created_at", table_name="agent_jobs")
    op.drop_index("ix_agent_jobs_workspace_created_at", table_name="agent_jobs")
    op.drop_index("ix_agent_jobs_user_created_at", table_name="agent_jobs")
    op.drop_index("ix_agent_jobs_run_id", table_name="agent_jobs")
    op.drop_index("ix_agent_jobs_celery_task_id", table_name="agent_jobs")
    op.drop_index("ix_agent_jobs_cancel_requested", table_name="agent_jobs")
    op.drop_index("ix_agent_jobs_status", table_name="agent_jobs")
    op.drop_index("ix_agent_jobs_conversation_id", table_name="agent_jobs")
    op.drop_index("ix_agent_jobs_workspace_id", table_name="agent_jobs")
    op.drop_index("ix_agent_jobs_user_id", table_name="agent_jobs")
    op.drop_table("agent_jobs")
