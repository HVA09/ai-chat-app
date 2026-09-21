"""إضافة المهام المجدولة لطلبات AI.

Revision ID: 0046_scheduled_tasks
Revises: 0045_share_access_analytics
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0046_scheduled_tasks"
down_revision: Union[str, None] = "0045_share_access_analytics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scheduled_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column(
            "schedule_type",
            sa.Enum("once", "daily", "weekly", name="scheduledtasktype"),
            nullable=False,
        ),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_scheduled_tasks_user_id",
        "scheduled_tasks",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_scheduled_tasks_workspace_id",
        "scheduled_tasks",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_scheduled_tasks_is_active",
        "scheduled_tasks",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        "ix_scheduled_tasks_user_active_next_run",
        "scheduled_tasks",
        ["user_id", "is_active", "next_run_at"],
        unique=False,
    )
    op.create_index(
        "ix_scheduled_tasks_workspace_active_next_run",
        "scheduled_tasks",
        ["workspace_id", "is_active", "next_run_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scheduled_tasks_workspace_active_next_run",
        table_name="scheduled_tasks",
    )
    op.drop_index(
        "ix_scheduled_tasks_user_active_next_run",
        table_name="scheduled_tasks",
    )
    op.drop_index("ix_scheduled_tasks_is_active", table_name="scheduled_tasks")
    op.drop_index("ix_scheduled_tasks_workspace_id", table_name="scheduled_tasks")
    op.drop_index("ix_scheduled_tasks_user_id", table_name="scheduled_tasks")
    op.drop_table("scheduled_tasks")
    op.execute("DROP TYPE IF EXISTS scheduledtasktype")
