"""إضافة مقاطع RAG وpgvector للبحث الدلالي.

Revision ID: 0016_rag_file_chunks
Revises: 0015_file_extracted_text
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0016_rag_file_chunks"
down_revision: Union[str, None] = "0015_file_extracted_text"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "file_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["file_attachments.id"],
            name="fk_file_chunks_file_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "file_id",
            "chunk_index",
            name="uq_file_chunks_file_index",
        ),
    )

    op.execute(
        """
        ALTER TABLE file_chunks
        ALTER COLUMN embedding TYPE vector(768)
        USING CASE
            WHEN embedding IS NULL THEN NULL
            ELSE embedding::vector
        END
        """
    )

    op.create_index(
        "ix_file_chunks_file_id",
        "file_chunks",
        ["file_id"],
        unique=False,
    )
    op.create_index(
        "ix_file_chunks_embedding_hnsw",
        "file_chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_file_chunks_embedding_hnsw", table_name="file_chunks")
    op.drop_index("ix_file_chunks_file_id", table_name="file_chunks")
    op.drop_table("file_chunks")
