"""Create durable upload-processing jobs / transactional outbox.

Revision ID: 0085_upload_processing_jobs
Revises: 0084_upload_cleanup_intents
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0085_upload_processing_jobs"
down_revision: Union[str, None] = "0084_upload_cleanup_intents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "upload_processing_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "lease_id",
            sa.String(length=36),
            sa.ForeignKey("upload_leases.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(length=16), nullable=False),
        sa.Column("stage_revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending_dispatch"),
        sa.Column("generation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("owner_token_hash", sa.String(length=64), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "lease_id", "stage", "stage_revision",
            name="uq_upload_processing_jobs_lease_stage_revision",
        ),
        sa.CheckConstraint(
            "stage IN ('extract', 'index')",
            name="ck_upload_processing_jobs_stage",
        ),
        sa.CheckConstraint(
            "status IN ('pending_dispatch', 'queued', 'processing', 'retry_wait', "
            "'succeeded', 'failed_terminal', 'cancelled')",
            name="ck_upload_processing_jobs_status",
        ),
        sa.CheckConstraint("generation >= 0", name="ck_upload_processing_jobs_generation_nonnegative"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_upload_processing_jobs_attempt_nonnegative"),
        sa.CheckConstraint("max_attempts > 0", name="ck_upload_processing_jobs_max_attempts_positive"),
        sa.CheckConstraint("stage_revision > 0", name="ck_upload_processing_jobs_revision_positive"),
    )
    op.create_index(
        "ix_upload_processing_jobs_dispatch",
        "upload_processing_jobs",
        ["status", "available_at", "created_at"],
    )
    op.create_index(
        "ix_upload_processing_jobs_lease_status",
        "upload_processing_jobs",
        ["lease_id", "status"],
    )
    op.execute('ALTER TABLE public."upload_processing_jobs" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_index("ix_upload_processing_jobs_lease_status", table_name="upload_processing_jobs")
    op.drop_index("ix_upload_processing_jobs_dispatch", table_name="upload_processing_jobs")
    op.drop_table("upload_processing_jobs")
