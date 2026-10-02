"""Persistent steps for multi-stage Agent workflows (F5.1)."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class AgentWorkflowStep(Base):
    __tablename__ = "agent_workflow_steps"
    __table_args__ = (
        UniqueConstraint(
            "agent_job_id",
            "sequence",
            name="uq_agent_workflow_steps_job_sequence",
        ),
        Index(
            "ix_agent_workflow_steps_job_status",
            "agent_job_id",
            "status",
        ),
        Index(
            "ix_agent_workflow_steps_job_sequence",
            "agent_job_id",
            "sequence",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_job_id: Mapped[int] = mapped_column(
        ForeignKey("agent_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="queued",
        server_default="queued",
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_sources: Mapped[list | None] = mapped_column(JSON, nullable=True)
    checkpoint: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job = relationship("AgentJob", back_populates="workflow_steps")
