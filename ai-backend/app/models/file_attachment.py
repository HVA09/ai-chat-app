"""
نموذج الملفات المرفوعة — البيانات الوصفية بقاعدة البيانات، والملف نفسه على القرص
"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class FileAttachment(Base):
    __tablename__ = "file_attachments"
    __table_args__ = (Index("ix_file_attachments_user_id_created_at", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[int | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    workspace = relationship("Workspace", back_populates="file_attachments")
    conversation_links = relationship(
        "ConversationFileLink", back_populates="file", cascade="all, delete-orphan", passive_deletes=True
    )
    chunks = relationship(
        "FileChunk", back_populates="file", cascade="all, delete-orphan", passive_deletes=True
    )
