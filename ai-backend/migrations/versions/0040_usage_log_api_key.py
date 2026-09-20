"""ربط سجلات استخدام AI بمفتاح API الشخصي.

Revision ID: 0040_usage_log_api_key
Revises: 0039_user_api_keys
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0040_usage_log_api_key"
down_revision: Union[str, None] = "0039_user_api_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "usage_logs",
        sa.Column("api_key_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_usage_logs_api_key_id",
        "usage_logs",
        ["api_key_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_usage_logs_api_key_id_api_keys",
        "usage_logs",
        "api_keys",
        ["api_key_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_usage_logs_api_key_id_api_keys",
        "usage_logs",
        type_="foreignkey",
    )
    op.drop_index("ix_usage_logs_api_key_id", table_name="usage_logs")
    op.drop_column("usage_logs", "api_key_id")
