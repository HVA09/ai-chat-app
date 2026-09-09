"""إضافة سجل أحداث الدفع لمنع تكرار معالجة webhooks.

Revision ID: 0010_webhook_events
Revises: 0009_auth_session_hardening
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010_webhook_events"
down_revision: Union[str, None] = "0009_auth_session_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("provider", "event_hash", name="uq_webhook_events_provider_hash"),
    )


def downgrade() -> None:
    op.drop_table("webhook_events")
