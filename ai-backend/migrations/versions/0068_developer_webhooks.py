"""Add developer webhook endpoints and delivery history.

Revision ID: 0068_developer_webhooks
Revises: 0067_scheduled_agents
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0068_developer_webhooks"
down_revision: Union[str, None] = "0067_scheduled_agents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "webhook_endpoints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("secret_encrypted", sa.Text(), nullable=False),
        sa.Column("event_types", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_webhook_endpoints_user_id",
        "webhook_endpoints",
        ["user_id"],
    )
    op.create_index(
        "ix_webhook_endpoints_user_id_created_at",
        "webhook_endpoints",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_webhook_endpoints_user_id_active",
        "webhook_endpoints",
        ["user_id", "is_active"],
    )

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "webhook_endpoint_id",
            sa.Integer(),
            sa.ForeignKey("webhook_endpoints.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "webhook_endpoint_id",
            "event_id",
            name="uq_webhook_deliveries_endpoint_event",
        ),
    )
    op.create_index(
        "ix_webhook_deliveries_endpoint_id",
        "webhook_deliveries",
        ["webhook_endpoint_id"],
    )
    op.create_index(
        "ix_webhook_deliveries_endpoint_created_at",
        "webhook_deliveries",
        ["webhook_endpoint_id", "created_at"],
    )
    op.create_index(
        "ix_webhook_deliveries_status_next_attempt_at",
        "webhook_deliveries",
        ["status", "next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_webhook_deliveries_status_next_attempt_at",
        table_name="webhook_deliveries",
    )
    op.drop_index(
        "ix_webhook_deliveries_endpoint_created_at",
        table_name="webhook_deliveries",
    )
    op.drop_index(
        "ix_webhook_deliveries_endpoint_id",
        table_name="webhook_deliveries",
    )
    op.drop_table("webhook_deliveries")
    op.drop_index(
        "ix_webhook_endpoints_user_id_active",
        table_name="webhook_endpoints",
    )
    op.drop_index(
        "ix_webhook_endpoints_user_id_created_at",
        table_name="webhook_endpoints",
    )
    op.drop_index("ix_webhook_endpoints_user_id", table_name="webhook_endpoints")
    op.drop_table("webhook_endpoints")
