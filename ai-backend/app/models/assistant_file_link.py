"""ربط الملفات بالمعاونين المخصصين لاستخدامها كمعرفة دائمة."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class AssistantFileLink(Base):
    __tablename__ = "assistant_file_links"

    assistant_id: Mapped[int] = mapped_column(
        ForeignKey("assistants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    file_id: Mapped[int] = mapped_column(
        ForeignKey("file_attachments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    assistant = relationship("Assistant", back_populates="file_links")
    file = relationship("FileAttachment", back_populates="assistant_links")
