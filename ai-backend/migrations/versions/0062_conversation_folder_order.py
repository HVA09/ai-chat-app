"""إضافة ترتيب ثابت لمجلدات المحادثات.

Revision ID: 0062_conversation_folder_order
Revises: 0061_conversation_folder_colors
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0062_conversation_folder_order"
down_revision: Union[str, None] = "0061_conversation_folder_colors"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversation_folders",
        sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"),
    )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            WITH ordered AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY user_id, workspace_id
                        ORDER BY created_at ASC, id ASC
                    ) - 1 AS new_order
                FROM conversation_folders
            )
            UPDATE conversation_folders AS folders
            SET sort_order = ordered.new_order
            FROM ordered
            WHERE folders.id = ordered.id
            """
        )
    )

    op.alter_column(
        "conversation_folders",
        "sort_order",
        nullable=False,
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("conversation_folders", "sort_order")
