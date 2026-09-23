"""إضافة روابط عامة آمنة للمساعدين المخصصين.

Revision ID: 0064_public_assistants
Revises: 0063_user_sessions
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0064_public_assistants"
down_revision: Union[str, None] = "0063_user_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assistants",
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "assistants",
        sa.Column("public_token", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_assistants_public_token",
        "assistants",
        ["public_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_assistants_public_token", table_name="assistants")
    op.drop_column("assistants", "public_token")
    op.drop_column("assistants", "is_public")
