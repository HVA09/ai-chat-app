"""Versioned snapshots of a knowledge-base file set."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class KnowledgeBaseVersion(Base):
    __tablename__ = "knowledge_base_versions"
    __table_args__ = (
        UniqueConstraint(
            "scope_type",
            "scope_id",
            "version",
            name="uq_knowledge_base_versions_scope_version",
        ),
        Index(
            "ix_knowledge_base_versions_scope_created_at",
            "scope_type",
            "scope_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_id: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    file_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    created_by = relationship("User")
