"""Add a durable outbox for object-storage cleanup.

Revision ID: 0083_storage_cleanup_outbox
Revises: 0082_file_index_fingerprints
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0083_storage_cleanup_outbox"
down_revision: Union[str, None] = "0082_file_index_fingerprints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "storage_cleanup_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        # Deliberately no FK to users: account deletion must not cascade away
        # the durable instruction that removes the user's external objects.
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=True),
        # Stored relative to UPLOAD_DIR; workers validate it before unlinking.
        sa.Column("fallback_path", sa.String(length=1024), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "operation IN ('delete_user_prefix', 'delete_file')",
            name="ck_storage_cleanup_outbox_operation",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_storage_cleanup_outbox_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_storage_cleanup_outbox_attempt_count",
        ),
        sa.CheckConstraint(
            "(operation = 'delete_user_prefix' AND user_id IS NOT NULL) OR "
            "(operation = 'delete_file' AND object_key IS NOT NULL AND fallback_path IS NOT NULL)",
            name="ck_storage_cleanup_outbox_payload",
        ),
    )
    op.create_index(
        "ix_storage_cleanup_outbox_due",
        "storage_cleanup_outbox",
        ["status", "available_at", "id"],
    )
    op.create_index(
        "ix_storage_cleanup_outbox_lease",
        "storage_cleanup_outbox",
        ["status", "locked_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_storage_cleanup_outbox_lease", table_name="storage_cleanup_outbox")
    op.drop_index("ix_storage_cleanup_outbox_due", table_name="storage_cleanup_outbox")
    op.drop_table("storage_cleanup_outbox")
