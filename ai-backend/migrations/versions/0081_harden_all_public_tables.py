"""Codify the production RLS baseline for every public application table.

Revision ID: 0081_harden_all_public_tables
Revises: 0080_harden_public_rls

Production was verified on 2026-11-09 to have RLS enabled on all 46
public tables. This migration makes that posture reproducible on fresh
Stage databases and future deployments.

No policies are created here: the app accesses PostgreSQL through its
privileged backend connection, while Supabase Data API roles remain
default-deny unless separately and deliberately configured.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0081_harden_all_public_tables"
down_revision: Union[str, None] = "0080_harden_public_rls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Public tables observed in the production database at the time this
# migration was authored. Keep this explicit: do not change unrelated
# Supabase-managed tables in the public schema.
_PUBLIC_TABLES = (
    "alembic_version",
    "agent_jobs",
    "agent_workflow_steps",
    "api_keys",
    "assistant_file_links",
    "assistant_versions",
    "assistant_workspace_shares",
    "assistants",
    "audit_logs",
    "conversation_comments",
    "conversation_file_links",
    "conversation_folders",
    "conversation_shares",
    "conversation_tag_links",
    "conversation_tags",
    "conversation_workspace_shares",
    "conversations",
    "file_attachments",
    "file_chunks",
    "messages",
    "notifications",
    "oauth_connections",
    "oauth_states",
    "plans",
    "project_files",
    "project_members",
    "project_memories",
    "project_preview_artifacts",
    "saved_prompt_versions",
    "saved_prompts",
    "scheduled_task_runs",
    "scheduled_tasks",
    "subscriptions",
    "usage_logs",
    "user_memories",
    "user_sessions",
    "users",
    "webhook_deliveries",
    "webhook_endpoints",
    "webhook_events",
    "workspace_invitations",
    "workspace_members",
    "workspace_projects",
    "workspace_rbac_permissions",
    "workspace_rbac_roles",
    "workspaces",
)


def upgrade() -> None:
    for table_name in _PUBLIC_TABLES:
        op.execute(
            f'ALTER TABLE IF EXISTS public."{table_name}" '
            "ENABLE ROW LEVEL SECURITY"
        )


def downgrade() -> None:
    # Security hardening is intentionally monotonic. Disabling RLS here
    # would weaken the production security baseline, so rollback retains it.
    pass
