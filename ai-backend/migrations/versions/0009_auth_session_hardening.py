"""إبطال الجلسات وتوسعة حقل سر TOTP

Revision ID: 0009_auth_session_hardening
Revises: 0008_notifications
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009_auth_session_hardening"
down_revision: Union[str, None] = "0008_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("users", "totp_secret", existing_type=sa.String(length=64), type_=sa.String(length=255), existing_nullable=True)


def downgrade() -> None:
    op.alter_column("users", "totp_secret", existing_type=sa.String(length=255), type_=sa.String(length=64), existing_nullable=True)
    op.drop_column("users", "token_version")
