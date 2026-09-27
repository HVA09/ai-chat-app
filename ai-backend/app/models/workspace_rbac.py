"""Enterprise workspace RBAC models for E6."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class WorkspaceRBACRole(Base):
    __tablename__ = "workspace_rbac_roles"
    __table_args__ = (
        Index("ix_workspace_rbac_roles_workspace_id", "workspace_id"),
        Index(
            "ix_workspace_rbac_roles_workspace_name",
            "workspace_id",
            "name",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    is_system: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    workspace = relationship("Workspace")
    created_by = relationship("User")
    permissions = relationship(
        "WorkspaceRBACPermission",
        cascade="all, delete-orphan",
        passive_deletes=True,
        back_populates="role",
    )


class WorkspaceRBACPermission(Base):
    __tablename__ = "workspace_rbac_permissions"
    __table_args__ = (Index("ix_workspace_rbac_permissions_role_id", "role_id"),)

    role_id: Mapped[int] = mapped_column(
        ForeignKey("workspace_rbac_roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission: Mapped[str] = mapped_column(String(100), primary_key=True)

    role = relationship("WorkspaceRBACRole", back_populates="permissions")
