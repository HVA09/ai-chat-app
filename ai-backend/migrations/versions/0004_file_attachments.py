"""إضافة جدول file_attachments

Revision ID: 0004_file_attachments
Revises: 0003_profile_fields
Create Date: 2026-07-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_file_attachments"
down_revision: Union[str, None] = "0003_profile_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "file_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_file_attachments_stored_filename", "file_attachments", ["stored_filename"], unique=True
    )
    op.create_index(
        "ix_file_attachments_user_id_created_at", "file_attachments", ["user_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("file_attachments")
