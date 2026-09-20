"""إضافة النموذج الافتراضي لمساحة العمل.

Revision ID: 0036_workspace_default_ai_model
Revises: 0035_assistant_workspace_shares
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0036_workspace_default_ai_model"
down_revision: Union[str, None] = "0035_assistant_workspace_shares"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column("default_ai_model", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workspaces", "default_ai_model")
