"""Project-level collaboration membership."""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class ProjectMemberRole(str, enum.Enum):
    viewer = "viewer"
    editor = "editor"
    manager = "manager"


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "user_id",
            name="uq_project_members_project_user",
        ),
        Index("ix_project_members_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("workspace_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[ProjectMemberRole] = mapped_column(
        Enum(ProjectMemberRole),
        default=ProjectMemberRole.viewer,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    project = relationship("WorkspaceProject", back_populates="members")
    user = relationship("User")
