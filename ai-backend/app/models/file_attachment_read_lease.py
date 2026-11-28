"""Short-lived leases protecting file readers from physical cleanup."""
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class FileAttachmentReadLease(Base):
    __tablename__ = "file_attachment_read_leases"
    __table_args__ = (
        Index("ix_file_attachment_read_leases_file_expiry", "file_attachment_id", "expires_at"),
        Index("ix_file_attachment_read_leases_user_expiry", "user_id", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Intentionally no FK: lease evidence must survive attachment/account cascades.
    file_attachment_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
