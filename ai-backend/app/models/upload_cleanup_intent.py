"""Durable intent to delete an upload object that never gained a committed attachment."""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class UploadCleanupIntent(Base):
    __tablename__ = "upload_cleanup_intents"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_upload_cleanup_intents_idempotency_key"),
        CheckConstraint("attempt_count >= 0", name="ck_upload_cleanup_intents_attempt_count_nonnegative"),
        CheckConstraint(
            "status IN ('pending', 'completed', 'blocked')",
            name="ck_upload_cleanup_intents_status",
        ),
        Index("ix_upload_cleanup_intents_status_next_attempt", "status", "next_attempt_at"),
        Index("ix_upload_cleanup_intents_user_created", "user_id", "created_at"),
        Index("ix_upload_cleanup_intents_lease_generation", "lease_id", "generation"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    # Nullable so the intent survives account deletion.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Optional link to the durable upload ownership record. The object key is
    # copied here and remains authoritative if the lease is later detached.
    lease_id: Mapped[str | None] = mapped_column(
        ForeignKey("upload_leases.id", ondelete="SET NULL"), nullable=True
    )
    generation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
