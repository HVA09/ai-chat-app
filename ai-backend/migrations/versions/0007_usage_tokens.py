"""إضافة أعمدة input_tokens/output_tokens لجدول usage_logs"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
revision: str = "0007_usage_tokens"
down_revision: Union[str, None] = "0006_subscriptions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("usage_logs", sa.Column("input_tokens", sa.Integer(), nullable=True)); op.add_column("usage_logs", sa.Column("output_tokens", sa.Integer(), nullable=True))

def downgrade() -> None:
    op.drop_column("usage_logs", "output_tokens"); op.drop_column("usage_logs", "input_tokens")
