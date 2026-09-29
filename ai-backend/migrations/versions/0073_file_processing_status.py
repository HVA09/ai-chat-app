"""Add asynchronous file processing status.

Revision ID: 0073_file_processing_status
Revises: 0072_platform_asset_versioning
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0073_file_processing_status"
down_revision: Union[str, None] = "0072_platform_asset_versioning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "file_attachments",
        sa.Column(
            "processing_status",
            sa.String(length=20),
            nullable=False,
            server_default="queued",
        ),
    )
    op.add_column(
        "file_attachments",
        sa.Column("processing_error", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_file_attachments_processing_status",
        "file_attachments",
        ["processing_status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_file_attachments_processing_status",
        table_name="file_attachments",
    )
    op.drop_column("file_attachments", "processing_error")
    op.drop_column("file_attachments", "processing_status")
