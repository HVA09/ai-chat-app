"""إضافة سجل تنفيذ المهام المجدولة.

Revision ID: 0047_scheduled_task_runs
Revises: 0046_scheduled_tasks
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0047_scheduled_task_runs"
down_revision: Union[str, None] = "0046_scheduled_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scheduled_task_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scheduled_task_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "running",
                "succeeded",
                "failed",
                name="scheduledtaskrunstatus",
            ),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["scheduled_task_id"],
            ["scheduled_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_scheduled_task_runs_scheduled_task_id",
        "scheduled_task_runs",
        ["scheduled_task_id"],
        unique=False,
    )
    op.create_index(
        "ix_scheduled_task_runs_user_id",
        "scheduled_task_runs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_scheduled_task_runs_workspace_id",
        "scheduled_task_runs",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_scheduled_task_runs_status",
        "scheduled_task_runs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_scheduled_task_runs_conversation_id",
        "scheduled_task_runs",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "ix_scheduled_task_runs_task_created_at",
        "scheduled_task_runs",
        ["scheduled_task_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_scheduled_task_runs_user_created_at",
        "scheduled_task_runs",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scheduled_task_runs_user_created_at",
        table_name="scheduled_task_runs",
    )
    op.drop_index(
        "ix_scheduled_task_runs_task_created_at",
        table_name="scheduled_task_runs",
    )
    op.drop_index(
        "ix_scheduled_task_runs_conversation_id",
        table_name="scheduled_task_runs",
    )
    op.drop_index(
        "ix_scheduled_task_runs_status",
        table_name="scheduled_task_runs",
    )
    op.drop_index(
        "ix_scheduled_task_runs_workspace_id",
        table_name="scheduled_task_runs",
    )
    op.drop_index(
        "ix_scheduled_task_runs_user_id",
        table_name="scheduled_task_runs",
    )
    op.drop_index(
        "ix_scheduled_task_runs_scheduled_task_id",
        table_name="scheduled_task_runs",
    )
    op.drop_table("scheduled_task_runs")
    op.execute("DROP TYPE IF EXISTS scheduledtaskrunstatus")
