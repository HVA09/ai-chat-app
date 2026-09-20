"""نموذج مجلدات تنظيم المحادثات للمستخدم ومساحة العمل."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class ConversationFolder(Base):
    __tablename__ = "conversation_folders"
    __table_args__ = (
        Index("ix_conversation_folders_user_id_created_at", "user_id", "created_at"),
        Index(
            "uq_conversation_folders_user_personal_name",
            "user_id",
            "name",
            unique=True,
            postgresql_where=ForeignKey("users.id") if False else None,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[int | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    owner = relationship("User", back_populates="conversation_folders")
    workspace = relationship("Workspace", back_populates="conversation_folders")
    conversations = relationship(
        "Conversation", back_populates="folder", passive_deletes=True
    )
