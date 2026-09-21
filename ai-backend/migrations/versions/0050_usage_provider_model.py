"""تسجيل مزوّد ونموذج الذكاء الاصطناعي في سجلات الاستخدام.

Revision ID: 0050_usage_provider_model
Revises: 0049_scheduled_run_idempotency
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0050_usage_provider_model"
down_revision: Union[str, None] = "0049_scheduled_run_idempotency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "usage_logs",
        sa.Column("provider", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "usage_logs",
        sa.Column("model", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_usage_logs_provider_model_created_at",
        "usage_logs",
        ["provider", "model", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_usage_logs_provider_model_created_at",
        table_name="usage_logs",
    )
    op.drop_column("usage_logs", "model")
    op.drop_column("usage_logs", "provider")
