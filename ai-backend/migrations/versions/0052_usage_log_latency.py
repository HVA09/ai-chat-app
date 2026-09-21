"""إضافة زمن استجابة طلبات الذكاء الاصطناعي إلى سجل الاستخدام.

Revision ID: 0052_usage_log_latency
Revises: 0051_usage_log_provider
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0052_usage_log_latency"
down_revision: Union[str, None] = "0051_usage_log_provider"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("usage_logs", sa.Column("latency_ms", sa.Integer(), nullable=True))
    op.create_index(
        "ix_usage_logs_provider_latency_created_at",
        "usage_logs",
        ["provider", "latency_ms", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_usage_logs_provider_latency_created_at",
        table_name="usage_logs",
    )
    op.drop_column("usage_logs", "latency_ms")
