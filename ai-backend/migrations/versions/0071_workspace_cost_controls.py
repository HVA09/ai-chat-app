"""Add workspace monthly AI cost budgets.

Revision ID: 0071_workspace_cost_controls
Revises: 0070_enterprise_rbac
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0071_workspace_cost_controls"
down_revision: Union[str, None] = "0070_enterprise_rbac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column("monthly_ai_budget_usd", sa.Numeric(12, 4), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workspaces", "monthly_ai_budget_usd")
