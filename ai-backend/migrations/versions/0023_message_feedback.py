"""إضافة تقييمات للردود المساعدة.

Revision ID: 0023_message_feedback
Revises: 0022_workspace_audit_logs
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0023_message_feedback"
down_revision: Union[str, None] = "0022_workspace_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("feedback", sa.SmallInteger(), nullable=True),
    )
    op.create_check_constraint(
        "ck_messages_feedback_valid",
        "messages",
        "feedback IS NULL OR feedback IN (-1, 1)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_messages_feedback_valid", "messages", type_="check")
    op.drop_column("messages", "feedback")
