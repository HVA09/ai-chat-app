"""Track project preview artifact metadata.

Revision ID: 0075_project_artifacts
Revises: 0074_project_collaboration
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0075_project_artifacts"
down_revision: Union[str, None] = "0074_project_collaboration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_artifacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("workspace_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("artifact_id", sa.String(length=64), nullable=False),
        sa.Column("entrypoint", sa.String(length=512), nullable=False),
        sa.Column("artifact_size_bytes", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "project_id",
            "artifact_id",
            name="uq_project_artifacts_project_artifact",
        ),
    )
    op.create_index(
        "ix_project_artifacts_project_id",
        "project_artifacts",
        ["project_id"],
    )
    op.create_index(
        "ix_project_artifacts_project_id_created_at",
        "project_artifacts",
        ["project_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_artifacts_project_id_created_at",
        table_name="project_artifacts",
    )
    op.drop_index("ix_project_artifacts_project_id", table_name="project_artifacts")
    op.drop_table("project_artifacts")
