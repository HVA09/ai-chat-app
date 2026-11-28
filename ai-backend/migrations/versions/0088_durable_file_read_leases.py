"""Preserve reader leases across attachment metadata deletion.

Revision ID: 0090_durable_file_read_leases
Revises: 0089_file_attachment_read_leases
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0090_durable_file_read_leases"
down_revision: Union[str, None] = "0089_file_attachment_read_leases"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Backfill ownership before removing the cascading attachment FK. This
    # allows active reader evidence to survive account/attachment cascades.
    op.add_column(
        "file_attachment_read_leases",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE file_attachment_read_leases AS leases
            SET user_id = attachments.user_id
            FROM file_attachments AS attachments
            WHERE attachments.id = leases.file_attachment_id
            """
        )
    )
    op.alter_column(
        "file_attachment_read_leases",
        "user_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.drop_constraint(
        "file_attachment_read_leases_file_attachment_id_fkey",
        "file_attachment_read_leases",
        type_="foreignkey",
    )
    op.create_index(
        "ix_file_attachment_read_leases_user_expiry",
        "file_attachment_read_leases",
        ["user_id", "expires_at"],
    )


def downgrade() -> None:
    # Orphaned leases cannot be reattached to deleted metadata. Remove those
    # records before restoring the original cascading FK.
    op.execute(
        sa.text(
            """
            DELETE FROM file_attachment_read_leases AS leases
            WHERE NOT EXISTS (
                SELECT 1
                FROM file_attachments AS attachments
                WHERE attachments.id = leases.file_attachment_id
            )
            """
        )
    )
    op.drop_index(
        "ix_file_attachment_read_leases_user_expiry",
        table_name="file_attachment_read_leases",
    )
    op.create_foreign_key(
        "file_attachment_read_leases_file_attachment_id_fkey",
        "file_attachment_read_leases",
        "file_attachments",
        ["file_attachment_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_column("file_attachment_read_leases", "user_id")
