"""Add object storage keys to file attachments.

Revision ID: 0065_object_storage
Revises: 0064_public_assistants
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0065_object_storage"
down_revision: Union[str, None] = "0064_public_assistants"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "file_attachments",
        sa.Column("object_key", sa.String(length=512), nullable=True),
    )
    op.create_index(
        "ix_file_attachments_object_key",
        "file_attachments",
        ["object_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_file_attachments_object_key", table_name="file_attachments")
    op.drop_column("file_attachments", "object_key")
