"""
نموذج الملفات المرفوعة — البيانات الوصفية بقاعدة البيانات، والملف نفسه على القرص
"""
import hashlib
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, event
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
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("workspace_projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    object_key: Mapped[str | None] = mapped_column(String(512), unique=True, nullable=True, index=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Hashes identify the exact normalized text and embedding space used for RAG.
    # Legacy rows remain NULL until reindexed; their old vectors are not trusted.
    extracted_text_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    indexed_text_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    indexed_embedding_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    indexed_embedding_provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    indexed_embedding_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    workspace = relationship("Workspace", back_populates="file_attachments")
    project = relationship("WorkspaceProject", back_populates="file_attachments")
    conversation_links = relationship(
        "ConversationFileLink", back_populates="file", cascade="all, delete-orphan", passive_deletes=True
    )
    chunks = relationship(
        "FileChunk", back_populates="file", cascade="all, delete-orphan", passive_deletes=True
    )
    assistant_links = relationship(
        "AssistantFileLink", back_populates="file", cascade="all, delete-orphan", passive_deletes=True
    )



def extracted_text_fingerprint(text: str | None) -> str | None:
    """SHA-256 of the normalized text shape consumed by chunk_text()."""
    normalized = " ".join((text or "").split())
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@event.listens_for(FileAttachment, "before_insert")
@event.listens_for(FileAttachment, "before_update")
def _sync_extracted_text_fingerprint(_mapper, _connection, attachment) -> None:
    """Keep the current-source fingerprint in sync with extracted_text."""
    attachment.extracted_text_sha256 = extracted_text_fingerprint(
        attachment.extracted_text
    )
