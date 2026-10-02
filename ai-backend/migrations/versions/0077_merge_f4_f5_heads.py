"""Merge the F4.3 and F5.1 Alembic heads.

Revision ID: 0077_merge_f4_f5_heads
Revises: 0076_project_name_conflict_index, 0076_agent_workflow_checkpoints
"""
from typing import Sequence, Union


revision: str = "0077_merge_f4_f5_heads"
down_revision: Union[str, tuple[str, str], None] = (
    "0076_project_name_conflict_index",
    "0076_agent_workflow_checkpoints",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
