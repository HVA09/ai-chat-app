"""دمج رأسي Alembic الناتجين عن 0032.

Revision ID: 0033_merge_migration_heads
Revises: 0032_message_bookmarks, 0032_workspace_files
"""
from typing import Sequence, Union


revision: str = "0033_merge_migration_heads"
down_revision: Union[str, tuple[str, str], None] = (
    "0032_message_bookmarks",
    "0032_workspace_files",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
