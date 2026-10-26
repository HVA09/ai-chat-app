"""Track source text and embedding identity for RAG indexes.

Revision ID: 0081_file_index_fingerprints
Revises: 0080_harden_public_rls
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0081_file_index_fingerprints"
down_revision: Union[str, None] = "0080_harden_public_rls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "file_attachments",
        sa.Column("extracted_text_sha256", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "file_attachments",
        sa.Column("indexed_text_sha256", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "file_attachments",
        sa.Column("indexed_embedding_fingerprint", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "file_attachments",
        sa.Column("indexed_embedding_provider", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "file_attachments",
        sa.Column("indexed_embedding_model", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "file_attachments",
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("file_attachments", "indexed_at")
    op.drop_column("file_attachments", "indexed_embedding_model")
    op.drop_column("file_attachments", "indexed_embedding_provider")
    op.drop_column("file_attachments", "indexed_embedding_fingerprint")
    op.drop_column("file_attachments", "indexed_text_sha256")
    op.drop_column("file_attachments", "extracted_text_sha256")
