"""إضافة المساعدين المخصصين وربطهم بالمحادثات.

Revision ID: 0018_custom_assistants
Revises: 0017_message_sources
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0018_custom_assistants"
down_revision: Union[str, None] = "0017_message_sources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assistants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_assistants_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id",
            "name",
            name="uq_assistants_user_name",
        ),
    )
    op.create_index(
        "ix_assistants_user_id",
        "assistants",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_assistants_user_id_created_at",
        "assistants",
        ["user_id", "created_at"],
        unique=False,
    )

    op.add_column(
        "conversations",
        sa.Column("assistant_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_conversations_assistant_id",
        "conversations",
        ["assistant_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_conversations_assistant_id_assistants",
        "conversations",
        "assistants",
        ["assistant_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_conversations_assistant_id_assistants",
        "conversations",
        type_="foreignkey",
    )
    op.drop_index("ix_conversations_assistant_id", table_name="conversations")
    op.drop_column("conversations", "assistant_id")
    op.drop_index("ix_assistants_user_id_created_at", table_name="assistants")
    op.drop_index("ix_assistants_user_id", table_name="assistants")
    op.drop_table("assistants")
