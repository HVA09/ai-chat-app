"""ربط الملفات بالمحادثات — يسمح باستخدام الملف في أكثر من محادثة."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class ConversationFileLink(Base):
    __tablename__ = "conversation_file_links"
    __table_args__ = (
        Index("ix_conversation_file_links_file_id", "file_id"),
    )

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    file_id: Mapped[int] = mapped_column(
        ForeignKey("file_attachments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversation = relationship("Conversation", back_populates="file_links")
    file = relationship("FileAttachment", back_populates="conversation_links")
