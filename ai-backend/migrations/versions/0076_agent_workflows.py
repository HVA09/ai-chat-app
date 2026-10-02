"""Add persistent multi-step Agent workflows and checkpoints.

Revision ID: 0076_agent_workflows
Revises: 0075_project_preview_artifacts
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0076_agent_workflows"
down_revision: Union[str, None] = "0075_project_preview_artifacts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_workflows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("current_step_position", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("checkpoint", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("result_text", sa.Text(), nullable=True),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["workspace_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_workflows_user_id", "agent_workflows", ["user_id"])
    op.create_index("ix_agent_workflows_workspace_id", "agent_workflows", ["workspace_id"])
    op.create_index("ix_agent_workflows_project_id", "agent_workflows", ["project_id"])
    op.create_index(
        "ix_agent_workflows_user_created_at",
        "agent_workflows",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_agent_workflows_workspace_created_at",
        "agent_workflows",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_agent_workflows_project_created_at",
        "agent_workflows",
        ["project_id", "created_at"],
    )
    op.create_index(
        "ix_agent_workflows_status_created_at",
        "agent_workflows",
        ["status", "created_at"],
    )
    op.create_index("ix_agent_workflows_status", "agent_workflows", ["status"])
    op.create_index(
        "ix_agent_workflows_cancel_requested",
        "agent_workflows",
        ["cancel_requested"],
    )

    op.create_table(
        "agent_workflow_steps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workflow_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("result_text", sa.Text(), nullable=True),
        sa.Column("result_sources", sa.JSON(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workflow_id"], ["agent_workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workflow_id",
            "position",
            name="uq_agent_workflow_steps_workflow_position",
        ),
    )
    op.create_index("ix_agent_workflow_steps_workflow_id", "agent_workflow_steps", ["workflow_id"])
    op.create_index(
        "ix_agent_workflow_steps_workflow_status",
        "agent_workflow_steps",
        ["workflow_id", "status"],
    )
    op.create_index("ix_agent_workflow_steps_status", "agent_workflow_steps", ["status"])


def downgrade() -> None:
    op.drop_index("ix_agent_workflow_steps_status", table_name="agent_workflow_steps")
    op.drop_index("ix_agent_workflow_steps_workflow_status", table_name="agent_workflow_steps")
    op.drop_index("ix_agent_workflow_steps_workflow_id", table_name="agent_workflow_steps")
    op.drop_table("agent_workflow_steps")

    op.drop_index("ix_agent_workflows_cancel_requested", table_name="agent_workflows")
    op.drop_index("ix_agent_workflows_status", table_name="agent_workflows")
    op.drop_index("ix_agent_workflows_status_created_at", table_name="agent_workflows")
    op.drop_index("ix_agent_workflows_project_created_at", table_name="agent_workflows")
    op.drop_index("ix_agent_workflows_workspace_created_at", table_name="agent_workflows")
    op.drop_index("ix_agent_workflows_user_created_at", table_name="agent_workflows")
    op.drop_index("ix_agent_workflows_project_id", table_name="agent_workflows")
    op.drop_index("ix_agent_workflows_workspace_id", table_name="agent_workflows")
    op.drop_index("ix_agent_workflows_user_id", table_name="agent_workflows")
    op.drop_table("agent_workflows")
