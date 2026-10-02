"""Add pause controls to AgentJob lifecycle.

Revision ID: 0079_agent_pause
Revises: 0078_agent_verify_retry
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0079_agent_pause"
down_revision: Union[str, None] = "0078_agent_verify_retry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agent_jobs",
        sa.Column("pause_requested", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("agent_jobs", "pause_requested")
