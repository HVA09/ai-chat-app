"""إضافة المنطقة الزمنية للمهام المجدولة.

Revision ID: 0048_scheduled_task_timezone
Revises: 0047_scheduled_task_runs
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0048_scheduled_task_timezone"
down_revision: Union[str, None] = "0047_scheduled_task_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scheduled_tasks",
        sa.Column(
            "timezone_name",
            sa.String(length=64),
            nullable=False,
            server_default="UTC",
        ),
    )


def downgrade() -> None:
    op.drop_column("scheduled_tasks", "timezone_name")
