"""نموذج مساحة العمل وعضوية المستخدمين فيها."""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class WorkspaceRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_workspaces_owner_name"),
        Index("ix_workspaces_owner_id_created_at", "owner_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    default_ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    daily_ai_request_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owner = relationship("User", back_populates="owned_workspaces")
    members = relationship(
        "WorkspaceMember",
        back_populates="workspace",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    conversations = relationship(
        "Conversation",
        back_populates="workspace",
        passive_deletes=True,
    )
    conversation_folders = relationship(
        "ConversationFolder",
        back_populates="workspace",
        passive_deletes=True,
    )
    projects = relationship(
        "WorkspaceProject",
        back_populates="workspace",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    conversation_shares = relationship(
        "ConversationWorkspaceShare",
        back_populates="workspace",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    assistant_shares = relationship(
        "AssistantWorkspaceShare",
        back_populates="workspace",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    file_attachments = relationship(
        "FileAttachment",
        back_populates="workspace",
        passive_deletes=True,
    )


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "user_id",
            name="uq_workspace_members_workspace_user",
        ),
        Index("ix_workspace_members_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[WorkspaceRole] = mapped_column(
        Enum(WorkspaceRole), default=WorkspaceRole.member, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="workspace_memberships")
