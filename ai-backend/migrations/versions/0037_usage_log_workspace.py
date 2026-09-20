"""ربط سجلات استخدام الذكاء الاصطناعي بمساحة العمل.

Revision ID: 0037_usage_log_workspace
Revises: 0036_workspace_default_ai_model
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0037_usage_log_workspace"
down_revision: Union[str, None] = "0036_workspace_default_ai_model"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "usage_logs",
        sa.Column("workspace_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_usage_logs_workspace_id",
        "usage_logs",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_usage_logs_workspace_id_created_at",
        "usage_logs",
        ["workspace_id", "created_at"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_usage_logs_workspace_id_workspaces",
        "usage_logs",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # السجلات القديمة لم تكن تحمل مساحة عمل. نربطها بأول مساحة يملكها
    # المستخدم (عادةً مساحته الشخصية) حتى لا تختفي من تقارير الاستخدام.
    op.execute(
        sa.text(
            """
            UPDATE usage_logs AS u
            SET workspace_id = (
                SELECT w.id
                FROM workspaces AS w
                WHERE w.owner_id = u.user_id
                ORDER BY w.created_at ASC, w.id ASC
                LIMIT 1
            )
            WHERE u.workspace_id IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_usage_logs_workspace_id_workspaces",
        "usage_logs",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_usage_logs_workspace_id_created_at",
        table_name="usage_logs",
    )
    op.drop_index(
        "ix_usage_logs_workspace_id",
        table_name="usage_logs",
    )
    op.drop_column("usage_logs", "workspace_id")
