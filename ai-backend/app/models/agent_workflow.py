"""Persistent multi-step Agent workflow state and checkpoints."""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class AgentWorkflow(Base):
    __tablename__ = "agent_workflows"
    __table_args__ = (
        Index("ix_agent_workflows_user_created_at", "user_id", "created_at"),
        Index("ix_agent_workflows_workspace_created_at", "workspace_id", "created_at"),
        Index("ix_agent_workflows_project_created_at", "project_id", "created_at"),
        Index("ix_agent_workflows_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("workspace_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued", server_default="queued", index=True
    )
    cancel_requested: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false", index=True
    )
    current_step_position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    checkpoint: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner = relationship("User")
    workspace = relationship("Workspace")
    project = relationship("WorkspaceProject")
    conversation = relationship("Conversation")
    steps = relationship(
        "AgentWorkflowStep",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="AgentWorkflowStep.position",
    )


class AgentWorkflowStep(Base):
    __tablename__ = "agent_workflow_steps"
    __table_args__ = (
        UniqueConstraint(
            "workflow_id",
            "position",
            name="uq_agent_workflow_steps_workflow_position",
        ),
        Index("ix_agent_workflow_steps_workflow_status", "workflow_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("agent_workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued", server_default="queued", index=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_sources: Mapped[list | None] = mapped_column(JSON, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(nullable=True)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workflow = relationship("AgentWorkflow", back_populates="steps")
