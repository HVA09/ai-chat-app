"""إضافة المزوّد الفعلي إلى سجلات استخدام الذكاء الاصطناعي.

Revision ID: 0051_usage_log_provider
Revises: 0050_usage_log_model
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0051_usage_log_provider"
down_revision: Union[str, None] = "0050_usage_log_model"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("usage_logs", sa.Column("provider", sa.String(length=50), nullable=True))
    op.create_index(
        "ix_usage_logs_provider_created_at",
        "usage_logs",
        ["provider", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_usage_logs_provider_created_at", table_name="usage_logs")
    op.drop_column("usage_logs", "provider")
