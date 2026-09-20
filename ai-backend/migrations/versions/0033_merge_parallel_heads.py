"""دمج مساري الترحيل الناتجين عن ملفات مساحة العمل والمفضلة.

Revision ID: 0033_merge_parallel_heads
Revises: 0032_workspace_files, 0032_message_bookmarks
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0033_merge_parallel_heads"
down_revision: Union[str, tuple[str, str], None] = (
    "0032_workspace_files",
    "0032_message_bookmarks",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
