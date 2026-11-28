"""Add bounded reader leases for file attachments.
Revision ID: 0089_file_attachment_read_leases
Revises: 0088_transactional_file_delete
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0089_file_attachment_read_leases"
down_revision: Union[str, None] = "0088_transactional_file_delete"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "file_attachment_read_leases",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "file_attachment_id",
            sa.Integer(),
            sa.ForeignKey("file_attachments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_file_attachment_read_leases_file_expiry",
        "file_attachment_read_leases",
        ["file_attachment_id", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_file_attachment_read_leases_file_expiry", table_name="file_attachment_read_leases")
    op.drop_table("file_attachment_read_leases")
