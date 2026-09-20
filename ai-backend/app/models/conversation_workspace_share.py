"""مشاركة محادثة للقراءة فقط مع أعضاء مساحة العمل."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class ConversationWorkspaceShare(Base):
    __tablename__ = "conversation_workspace_shares"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "workspace_id",
            name="uq_conversation_workspace_share",
        ),
        Index(
            "ix_conversation_workspace_shares_workspace_created",
            "workspace_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shared_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    conversation = relationship("Conversation", back_populates="workspace_shares")
    workspace = relationship("Workspace", back_populates="conversation_shares")
    shared_by = relationship("User")
