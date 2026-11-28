"""Add lease ownership fencing to storage cleanup outbox.

Revision ID: 0086_storage_cleanup_lease_token
Revises: 0085_storage_cleanup_outbox
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0086_storage_cleanup_lease_token"
down_revision: Union[str, None] = "0085_storage_cleanup_outbox"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "storage_cleanup_outbox",
        sa.Column("lease_token", sa.String(length=36), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("storage_cleanup_outbox", "lease_token")
