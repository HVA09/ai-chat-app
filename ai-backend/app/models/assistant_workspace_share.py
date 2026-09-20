"""مشاركة المساعد المخصص للقراءة والاستخدام مع أعضاء مساحة العمل."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class AssistantWorkspaceShare(Base):
    __tablename__ = "assistant_workspace_shares"
    __table_args__ = (
        UniqueConstraint(
            "assistant_id",
            "workspace_id",
            name="uq_assistant_workspace_share",
        ),
        Index(
            "ix_assistant_workspace_shares_workspace_created",
            "workspace_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assistant_id: Mapped[int] = mapped_column(
        ForeignKey("assistants.id", ondelete="CASCADE"),
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

    assistant = relationship("Assistant", back_populates="workspace_shares")
    workspace = relationship("Workspace", back_populates="assistant_shares")
    shared_by = relationship("User")
