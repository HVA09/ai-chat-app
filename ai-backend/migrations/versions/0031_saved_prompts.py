"""إضافة مكتبة الموجهات المحفوظة.

Revision ID: 0031_saved_prompts
Revises: 0030_conversation_summary
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0031_saved_prompts"
down_revision: Union[str, None] = "0030_conversation_summary"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "saved_prompts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_saved_prompts_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id",
            "name",
            name="uq_saved_prompts_user_name",
        ),
    )
    op.create_index(
        "ix_saved_prompts_user_id",
        "saved_prompts",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_saved_prompts_user_id_created_at",
        "saved_prompts",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_saved_prompts_user_id_created_at",
        table_name="saved_prompts",
    )
    op.drop_index("ix_saved_prompts_user_id", table_name="saved_prompts")
    op.drop_table("saved_prompts")
