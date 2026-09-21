"""Add optional passwords to conversation share links.

Revision ID: 0044_password_protected_shares
Revises: 0043_conversation_branch_links
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0044_password_protected_shares"
down_revision: Union[str, None] = "0043_conversation_branch_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversation_shares",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversation_shares", "password_hash")
