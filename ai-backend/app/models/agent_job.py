"""Persistent long-running Agent Platform jobs."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class AgentJob(Base):
    __tablename__ = "agent_jobs"
    __table_args__ = (
        Index("ix_agent_jobs_user_created_at", "user_id", "created_at"),
        Index("ix_agent_jobs_workspace_created_at", "workspace_id", "created_at"),
        Index("ix_agent_jobs_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued", server_default="queued", index=True
    )
    cancel_requested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    workflow_phase: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued", server_default="queued", index=True
    )
    retry_count: Mapped[int] = mapped_column(
        nullable=False, default=0, server_default="0"
    )
    max_retries: Mapped[int] = mapped_column(
        nullable=False, default=2, server_default="2"
    )
    checkpoint: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    checkpoint_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    agent_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default="agent-1", server_default="agent-1"
    )
    tool_policy_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_sources: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner = relationship("User")
    workspace = relationship("Workspace")
    conversation = relationship("Conversation")
