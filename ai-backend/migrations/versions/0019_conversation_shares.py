"""Add secure read-only conversation share links.

Revision ID: 0019_conversation_shares
Revises: 0018_custom_assistants
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0019_conversation_shares"
down_revision: Union[str, None] = "0018_custom_assistants"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_shares",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_conversation_shares_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "token_hash",
            name="uq_conversation_shares_token_hash",
        ),
    )
    op.create_index(
        "ix_conversation_shares_conversation_id",
        "conversation_shares",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_shares_conversation_id_created_at",
        "conversation_shares",
        ["conversation_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_shares_expires_at",
        "conversation_shares",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_shares_expires_at", table_name="conversation_shares")
    op.drop_index(
        "ix_conversation_shares_conversation_id_created_at",
        table_name="conversation_shares",
    )
    op.drop_index("ix_conversation_shares_conversation_id", table_name="conversation_shares")
    op.drop_table("conversation_shares")
