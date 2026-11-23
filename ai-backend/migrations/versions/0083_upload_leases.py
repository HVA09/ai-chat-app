"""Create durable upload lease records.

Revision ID: 0083_upload_leases
Revises: 0082_file_index_fingerprints
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0083_upload_leases"
down_revision: Union[str, None] = "0082_file_index_fingerprints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "upload_leases",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("staging_key", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="receiving"),
        sa.Column("generation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("owner_token_hash", sa.String(length=64), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "attachment_id",
            sa.Integer(),
            sa.ForeignKey("file_attachments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("object_key", name="uq_upload_leases_object_key"),
    )
    op.create_index("ix_upload_leases_user_id", "upload_leases", ["user_id"])
    op.create_index("ix_upload_leases_attachment_id", "upload_leases", ["attachment_id"])
    op.create_index(
        "ix_upload_leases_status_expires_at",
        "upload_leases",
        ["status", "expires_at"],
    )
    op.create_index(
        "ix_upload_leases_user_created_at",
        "upload_leases",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_upload_leases_user_created_at", table_name="upload_leases")
    op.drop_index("ix_upload_leases_status_expires_at", table_name="upload_leases")
    op.drop_index("ix_upload_leases_attachment_id", table_name="upload_leases")
    op.drop_index("ix_upload_leases_user_id", table_name="upload_leases")
    op.drop_table("upload_leases")
