"""منع تكرار التنفيذ المجدول لنفس الموعد.

Revision ID: 0049_scheduled_run_idempotency
Revises: 0048_scheduled_task_timezone
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0049_scheduled_run_idempotency"
down_revision: Union[str, None] = "0048_scheduled_task_timezone"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scheduled_task_runs",
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_scheduled_task_runs_scheduled_for",
        "scheduled_task_runs",
        ["scheduled_for"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_scheduled_task_runs_task_scheduled_for",
        "scheduled_task_runs",
        ["scheduled_task_id", "scheduled_for"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_scheduled_task_runs_task_scheduled_for",
        "scheduled_task_runs",
        type_="unique",
    )
    op.drop_index(
        "ix_scheduled_task_runs_scheduled_for",
        table_name="scheduled_task_runs",
    )
    op.drop_column("scheduled_task_runs", "scheduled_for")
