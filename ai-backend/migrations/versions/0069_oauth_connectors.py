"""Add OAuth connector connections and PKCE state.

Revision ID: 0069_oauth_connectors
Revises: 0068_developer_webhooks
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0069_oauth_connectors"
down_revision: Union[str, None] = "0068_developer_webhooks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oauth_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column(
            "token_type",
            sa.String(length=40),
            nullable=False,
            server_default="Bearer",
        ),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
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
            "user_id",
            "provider",
            "subject",
            name="uq_oauth_connections_user_provider_subject",
        ),
    )
    op.create_index(
        "ix_oauth_connections_user_id",
        "oauth_connections",
        ["user_id"],
    )
    op.create_index(
        "ix_oauth_connections_provider",
        "oauth_connections",
        ["provider"],
    )
    op.create_index(
        "ix_oauth_connections_user_id_created_at",
        "oauth_connections",
        ["user_id", "created_at"],
    )

    op.create_table(
        "oauth_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("code_verifier_encrypted", sa.Text(), nullable=False),
        sa.Column("redirect_uri", sa.String(length=2048), nullable=False),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("state_hash", name="uq_oauth_states_state_hash"),
    )
    op.create_index(
        "ix_oauth_states_user_id",
        "oauth_states",
        ["user_id"],
    )
    op.create_index(
        "ix_oauth_states_expires_at",
        "oauth_states",
        ["expires_at"],
    )
    op.create_index(
        "ix_oauth_states_user_created_at",
        "oauth_states",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_oauth_states_user_created_at",
        table_name="oauth_states",
    )
    op.drop_index(
        "ix_oauth_states_expires_at",
        table_name="oauth_states",
    )
    op.drop_index("ix_oauth_states_user_id", table_name="oauth_states")
    op.drop_table("oauth_states")

    op.drop_index(
        "ix_oauth_connections_user_id_created_at",
        table_name="oauth_connections",
    )
    op.drop_index(
        "ix_oauth_connections_provider",
        table_name="oauth_connections",
    )
    op.drop_index(
        "ix_oauth_connections_user_id",
        table_name="oauth_connections",
    )
    op.drop_table("oauth_connections")
