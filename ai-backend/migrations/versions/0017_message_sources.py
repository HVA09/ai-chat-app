"""إضافة مصادر RAG لرسائل المساعد.

Revision ID: 0017_message_sources
Revises: 0016_rag_file_chunks
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0017_message_sources"
down_revision: Union[str, None] = "0016_rag_file_chunks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("sources", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messages", "sources")
