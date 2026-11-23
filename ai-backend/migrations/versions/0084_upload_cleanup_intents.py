"""Create durable upload object-cleanup intents.

Revision ID: 0084_upload_cleanup_intents
Revises: 0083_upload_leases
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0084_upload_cleanup_intents"
down_revision: Union[str, None] = "0083_upload_leases"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "upload_cleanup_intents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "lease_id",
            sa.String(length=36),
            sa.ForeignKey("upload_leases.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("generation", sa.Integer(), nullable=True),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("idempotency_key", name="uq_upload_cleanup_intents_idempotency_key"),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_upload_cleanup_intents_attempt_count_nonnegative",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'blocked')",
            name="ck_upload_cleanup_intents_status",
        ),
    )
    op.create_index(
        "ix_upload_cleanup_intents_user_id",
        "upload_cleanup_intents",
        ["user_id"],
    )
    op.create_index(
        "ix_upload_cleanup_intents_status_next_attempt",
        "upload_cleanup_intents",
        ["status", "next_attempt_at"],
    )
    op.create_index(
        "ix_upload_cleanup_intents_user_created",
        "upload_cleanup_intents",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_upload_cleanup_intents_lease_generation",
        "upload_cleanup_intents",
        ["lease_id", "generation"],
    )
    op.execute('ALTER TABLE public."upload_cleanup_intents" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_index("ix_upload_cleanup_intents_lease_generation", table_name="upload_cleanup_intents")
    op.drop_index("ix_upload_cleanup_intents_user_created", table_name="upload_cleanup_intents")
    op.drop_index("ix_upload_cleanup_intents_status_next_attempt", table_name="upload_cleanup_intents")
    op.drop_index("ix_upload_cleanup_intents_user_id", table_name="upload_cleanup_intents")
    op.drop_table("upload_cleanup_intents")
