"""نموذج المشاريع داخل مساحة العمل لتنظيم المحادثات."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class WorkspaceProject(Base):
    __tablename__ = "workspace_projects"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_workspace_projects_workspace_name"),
        Index("ix_workspace_projects_workspace_id_created_at", "workspace_id", "created_at"),
        Index("ix_workspace_projects_owner_id", "owner_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assistant_id: Mapped[int | None] = mapped_column(
        ForeignKey("assistants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workspace = relationship("Workspace", back_populates="projects")
    owner = relationship("User", back_populates="owned_projects")
    assistant = relationship("Assistant")
    conversations = relationship(
        "Conversation",
        back_populates="project",
        passive_deletes=True,
    )
    file_attachments = relationship(
        "FileAttachment",
        back_populates="project",
        passive_deletes=True,
    )
    memories = relationship(
        "ProjectMemory",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
