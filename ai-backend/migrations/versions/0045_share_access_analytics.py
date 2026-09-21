"""Track conversation share access analytics.

Revision ID: 0045_share_access_analytics
Revises: 0044_password_protected_shares
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0045_share_access_analytics"
down_revision: Union[str, None] = "0044_password_protected_shares"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversation_shares",
        sa.Column("access_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "conversation_shares",
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversation_shares", "last_accessed_at")
    op.drop_column("conversation_shares", "access_count")
