"""Durable instructions for retryable object-storage cleanup."""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class StorageCleanupOutbox(Base):
    __tablename__ = "storage_cleanup_outbox"
    __table_args__ = (
        CheckConstraint(
            "operation IN ('delete_user_prefix', 'delete_file')",
            name="ck_storage_cleanup_outbox_operation",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_storage_cleanup_outbox_status",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_storage_cleanup_outbox_attempt_count",
        ),
        CheckConstraint(
            "(operation = 'delete_user_prefix' AND user_id IS NOT NULL) OR "
            "(operation = 'delete_file' AND object_key IS NOT NULL AND fallback_path IS NOT NULL)",
            name="ck_storage_cleanup_outbox_payload",
        ),
        Index("ix_storage_cleanup_outbox_due", "status", "available_at", "id"),
        Index("ix_storage_cleanup_outbox_lease", "status", "locked_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # No user or attachment FK: committed cleanup must survive account/row deletion.
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_attachment_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    storage_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("storage_profiles.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    fallback_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", server_default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
