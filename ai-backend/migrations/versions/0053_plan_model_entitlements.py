"""إضافة صلاحيات اختيار نماذج AI حسب خطة الاشتراك.

Revision ID: 0053_plan_model_entitlements
Revises: 0052_usage_log_latency
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0053_plan_model_entitlements"
down_revision: Union[str, None] = "0052_usage_log_latency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "plans",
        sa.Column(
            "allowed_models",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    # The Free plan stays on the configured default model.
    # Pro can use every model exposed through AI_ALLOWED_MODELS.
    op.execute(
        sa.text(
            "UPDATE plans SET allowed_models = CAST(:models AS JSON) "
            "WHERE name = :name"
        ),
        {"models": "[\"*\"]", "name": "Pro"},
    )


def downgrade() -> None:
    op.drop_column("plans", "allowed_models")
