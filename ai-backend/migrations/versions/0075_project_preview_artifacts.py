"""Add persistent project preview artifact lifecycle metadata.

Revision ID: 0075_project_preview_artifacts
Revises: 0074_project_collaboration
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0075_project_preview_artifacts"
down_revision: Union[str, None] = "0074_project_collaboration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_preview_artifacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("artifact_id", sa.String(length=64), nullable=False),
        sa.Column("entrypoint", sa.String(length=512), nullable=False),
        sa.Column("artifact_root", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("files_manifest", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["workspace_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "artifact_id",
            name="uq_project_preview_artifacts_project_artifact",
        ),
    )
    op.create_index(
        "ix_project_preview_artifacts_project_id",
        "project_preview_artifacts",
        ["project_id"],
    )
    op.create_index(
        "ix_project_preview_artifacts_project_status_created",
        "project_preview_artifacts",
        ["project_id", "status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_project_preview_artifacts_project_status_created", table_name="project_preview_artifacts")
    op.drop_index("ix_project_preview_artifacts_project_id", table_name="project_preview_artifacts")
    op.drop_table("project_preview_artifacts")
