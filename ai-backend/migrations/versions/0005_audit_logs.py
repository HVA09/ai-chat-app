"""إضافة جدول audit_logs"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
revision: str = "0005_audit_logs"
down_revision: Union[str, None] = "0004_file_attachments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table("audit_logs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), nullable=True), sa.Column("event_type", sa.String(length=50), nullable=False), sa.Column("description", sa.String(length=500), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"))
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

def downgrade() -> None:
    op.drop_table("audit_logs")
