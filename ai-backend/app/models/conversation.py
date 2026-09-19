"""
نماذج المحادثة والرسائل (Conversation / Message)
"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, String, Text, event, update
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.conversation_tag import conversation_tag_links


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        # يخدم GET /conversations: فلترة حسب user_id + ترتيب حسب created_at في استعلام واحد
        Index("ix_conversations_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), default="محادثة جديدة")
    is_pinned: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    is_archived: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    folder_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversation_folders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    assistant_id: Mapped[int | None] = mapped_column(
        ForeignKey("assistants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner = relationship("User", back_populates="conversations")
    folder = relationship("ConversationFolder", back_populates="conversations")
    workspace = relationship("Workspace", back_populates="conversations")
    assistant = relationship("Assistant", back_populates="conversations")
    tags = relationship(
        "ConversationTag",
        secondary=conversation_tag_links,
        back_populates="conversations",
        passive_deletes=True,
    )
    shares = relationship(
        "ConversationShare", back_populates="conversation", cascade="all, delete-orphan", passive_deletes=True
    )
    shares = relationship(
        "ConversationShare", back_populates="conversation", cascade="all, delete-orphan", passive_deletes=True
    )
    file_links = relationship(
        "ConversationFileLink", back_populates="conversation", cascade="all, delete-orphan", passive_deletes=True
    )
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    feedback: Mapped[int | None] = mapped_column(nullable=True)
    is_bookmarked: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")


@event.listens_for(Message, "after_insert")
@event.listens_for(Message, "after_delete")
def _touch_conversation_activity(mapper, connection, target):
    connection.execute(
        update(Conversation)
        .where(Conversation.id == target.conversation_id)
        .values(updated_at=func.now())
    )
