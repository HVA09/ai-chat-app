"""Secure share links for read-only conversation viewing."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class ConversationShare(Base):
    __tablename__ = "conversation_shares"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_conversation_shares_token_hash"),
        Index("ix_conversation_shares_conversation_id_created_at", "conversation_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    conversation = relationship("Conversation", back_populates="shares")
