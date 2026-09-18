"""مقاطع النص المستخرج من الملفات لاستخدامها في الاسترجاع قبل استدعاء AI."""
from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FileChunk(Base):
    __tablename__ = "file_chunks"
    __table_args__ = (
        UniqueConstraint("file_id", "chunk_index", name="uq_file_chunks_file_index"),
        Index("ix_file_chunks_file_id_chunk_index", "file_id", "chunk_index"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[int] = mapped_column(
        ForeignKey("file_attachments.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    file = relationship("FileAttachment", back_populates="chunks")
