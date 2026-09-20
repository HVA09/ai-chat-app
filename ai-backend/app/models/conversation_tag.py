"""نموذج وسائط tags للمحادثات."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Table, Column, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


conversation_tag_links = Table(
    "conversation_tag_links",
    Base.metadata,
    Column(
        "conversation_id",
        ForeignKey("conversations.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        ForeignKey("conversation_tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Index("ix_conversation_tag_links_tag_id", "tag_id"),
)


class ConversationTag(Base):
    __tablename__ = "conversation_tags"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_conversation_tags_user_name"),
        Index("ix_conversation_tags_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#64748B", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    owner = relationship("User", back_populates="conversation_tags")
    conversations = relationship(
        "Conversation",
        secondary=conversation_tag_links,
        back_populates="tags",
        passive_deletes=True,
    )
