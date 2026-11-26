"""Durable, idempotent stages for upload extraction and indexing."""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class UploadProcessingJob(Base):
    __tablename__ = "upload_processing_jobs"
    __table_args__ = (
        UniqueConstraint(
            "lease_id", "stage", "stage_revision",
            name="uq_upload_processing_jobs_lease_stage_revision",
        ),
        CheckConstraint(
            "stage IN ('extract', 'index')",
            name="ck_upload_processing_jobs_stage",
        ),
        CheckConstraint(
            "status IN ('pending_dispatch', 'queued', 'processing', 'retry_wait', "
            "'succeeded', 'failed_terminal', 'cancelled')",
            name="ck_upload_processing_jobs_status",
        ),
        CheckConstraint("generation >= 0", name="ck_upload_processing_jobs_generation_nonnegative"),
        CheckConstraint("attempt_count >= 0", name="ck_upload_processing_jobs_attempt_nonnegative"),
        CheckConstraint("max_attempts > 0", name="ck_upload_processing_jobs_max_attempts_positive"),
        CheckConstraint("stage_revision > 0", name="ck_upload_processing_jobs_revision_positive"),
        Index("ix_upload_processing_jobs_dispatch", "status", "available_at", "created_at"),
        Index("ix_upload_processing_jobs_lease_status", "lease_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    lease_id: Mapped[str] = mapped_column(
        ForeignKey("upload_leases.id", ondelete="RESTRICT"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(16), nullable=False)
    stage_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="pending_dispatch", server_default="pending_dispatch"
    )
    generation: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    owner_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=4, server_default="4")
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
