"""Track the AI model used for each usage event.

Revision ID: 0046_usage_log_model
Revises: 0045_share_access_analytics
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0046_usage_log_model"
down_revision: Union[str, None] = "0045_share_access_analytics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "usage_logs",
        sa.Column("model", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_usage_logs_model_created_at",
        "usage_logs",
        ["model", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_usage_logs_model_created_at", table_name="usage_logs")
    op.drop_column("usage_logs", "model")
