"""نماذج المهام المجدولة التي تنفذ طلبات AI تلقائيًا."""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Text, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class ScheduledTaskType(str, enum.Enum):
    once = "once"
    daily = "daily"
    weekly = "weekly"


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"
    __table_args__ = (
        Index("ix_scheduled_tasks_user_active_next_run", "user_id", "is_active", "next_run_at"),
        Index("ix_scheduled_tasks_workspace_active_next_run", "workspace_id", "is_active", "next_run_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    schedule_type: Mapped[ScheduledTaskType] = mapped_column(
        Enum(ScheduledTaskType), nullable=False
    )
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    weekday: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owner = relationship("User", back_populates="scheduled_tasks")
    workspace = relationship("Workspace", back_populates="scheduled_tasks")
