"""Harden exposed public tables with Row Level Security.

Revision ID: 0080_harden_public_rls
Revises: 0079_agent_pause
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0080_harden_public_rls"
down_revision: Union[str, None] = "0079_agent_pause"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLES = (
    "agent_jobs",
    "agent_workflow_steps",
    "oauth_connections",
    "oauth_states",
    "project_files",
    "project_members",
    "project_preview_artifacts",
    "saved_prompt_versions",
    "webhook_deliveries",
    "webhook_endpoints",
    "workspace_rbac_permissions",
    "workspace_rbac_roles",
)


def upgrade() -> None:
    for table in _TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
