"""Durable ownership records for file uploads and recovery bookkeeping.

Lease expiry is advisory only. It is never sufficient authorization to delete
an object; destructive recovery requires a separately verified worker fence.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class UploadLease(Base):
    __tablename__ = "upload_leases"
    __table_args__ = (
        UniqueConstraint("object_key", name="uq_upload_leases_object_key"),
        Index("ix_upload_leases_status_expires_at", "status", "expires_at"),
        Index("ix_upload_leases_user_created_at", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Keep the lease after account deletion so recovery metadata is not lost.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    staging_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="receiving", server_default="receiving"
    )
    generation: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    owner_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attachment_id: Mapped[int | None] = mapped_column(
        ForeignKey("file_attachments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
