"""تقسيم النص المستخرج إلى مقاطع للاسترجاع.

Revision ID: 0016_file_chunks
Revises: 0015_file_extracted_text
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0016_file_chunks"
down_revision: Union[str, None] = "0015_file_extracted_text"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "file_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["file_attachments.id"],
            name="fk_file_chunks_file_id_file_attachments",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "file_id",
            "chunk_index",
            name="uq_file_chunks_file_index",
        ),
    )
    op.create_index(
        "ix_file_chunks_file_id",
        "file_chunks",
        ["file_id"],
        unique=False,
    )
    op.create_index(
        "ix_file_chunks_file_id_chunk_index",
        "file_chunks",
        ["file_id", "chunk_index"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_file_chunks_file_id_chunk_index",
        table_name="file_chunks",
    )
    op.drop_index("ix_file_chunks_file_id", table_name="file_chunks")
    op.drop_table("file_chunks")
