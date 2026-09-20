"""Add selected AI model to usage logs.

Revision ID: 0041_usage_log_model
Revises: 0040_api_key_controls
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0041_usage_log_model"
down_revision: Union[str, None] = "0040_api_key_controls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("usage_logs", sa.Column("model", sa.String(length=100), nullable=True))
    op.create_index(
        "ix_usage_logs_model_created_at",
        "usage_logs",
        ["model", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_usage_logs_model_created_at", table_name="usage_logs")
    op.drop_column("usage_logs", "model")
