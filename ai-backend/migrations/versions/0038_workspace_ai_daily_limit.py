"""إضافة حد يومي اختياري لطلبات الذكاء الاصطناعي لمساحة العمل.

Revision ID: 0038_workspace_ai_daily_limit
Revises: 0037_usage_log_workspace
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0038_workspace_ai_daily_limit"
down_revision: Union[str, None] = "0037_usage_log_workspace"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column("daily_ai_request_limit", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workspaces", "daily_ai_request_limit")
