"""نماذج المساعدين المخصصين للمستخدم."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Assistant(Base):
    __tablename__ = "assistants"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_assistants_user_name"),
        Index("ix_assistants_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    owner = relationship("User", back_populates="assistants")
    conversations = relationship("Conversation", back_populates="assistant")
    workspace_shares = relationship(
        "AssistantWorkspaceShare", back_populates="assistant", cascade="all, delete-orphan", passive_deletes=True
    )
