"""Persist transactional individual-file cleanup ownership and target.
Revision ID: 0088_transactional_file_delete
Revises: 0087_storage_profiles
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0088_transactional_file_delete"
down_revision: Union[str, None] = "0087_storage_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "file_attachments",
        sa.Column("deletion_status", sa.String(24), nullable=False, server_default="available"),
    )
    op.create_check_constraint(
        "ck_file_attachments_deletion_status",
        "file_attachments",
        "deletion_status IN ('available', 'deletion_pending')",
    )
    op.add_column(
        "storage_cleanup_outbox",
        sa.Column("file_attachment_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_storage_cleanup_outbox_file_attachment_id",
        "storage_cleanup_outbox",
        ["file_attachment_id"],
    )
    op.add_column(
        "storage_cleanup_outbox",
        sa.Column("storage_profile_id", sa.String(64), nullable=True),
    )
    op.create_foreign_key(
        "fk_storage_cleanup_outbox_storage_profile_id_storage_profiles",
        "storage_cleanup_outbox",
        "storage_profiles",
        ["storage_profile_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_storage_cleanup_outbox_storage_profile_id",
        "storage_cleanup_outbox",
        ["storage_profile_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_storage_cleanup_outbox_storage_profile_id", table_name="storage_cleanup_outbox")
    op.drop_constraint(
        "fk_storage_cleanup_outbox_storage_profile_id_storage_profiles",
        "storage_cleanup_outbox",
        type_="foreignkey",
    )
    op.drop_column("storage_cleanup_outbox", "storage_profile_id")
    op.drop_index("ix_storage_cleanup_outbox_file_attachment_id", table_name="storage_cleanup_outbox")
    op.drop_column("storage_cleanup_outbox", "file_attachment_id")
    op.drop_constraint("ck_file_attachments_deletion_status", "file_attachments", type_="check")
    op.drop_column("file_attachments", "deletion_status")
