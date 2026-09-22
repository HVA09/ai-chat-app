"""ذاكرة مشتركة خاصة بالمشروع يستخدمها الذكاء الاصطناعي مع محادثات المشروع."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class ProjectMemory(Base):
    __tablename__ = "project_memories"
    __table_args__ = (
        Index("ix_project_memories_project_id_updated_at", "project_id", "updated_at"),
        Index("ix_project_memories_created_by_user_id", "created_by_user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("workspace_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project = relationship("WorkspaceProject", back_populates="memories")
    created_by = relationship("User", back_populates="project_memories")
