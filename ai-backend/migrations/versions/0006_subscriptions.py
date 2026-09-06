"""إضافة جدولي plans وsubscriptions + خطتين افتراضيتين (Free وPro)"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
revision: str = "0006_subscriptions"
down_revision: Union[str, None] = "0005_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table("plans", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(length=100), nullable=False), sa.Column("price_cents", sa.Integer(), nullable=False), sa.Column("currency", sa.String(length=3), nullable=False, server_default="usd"), sa.Column("interval", sa.String(length=20), nullable=False, server_default="month"), sa.Column("daily_ai_request_limit", sa.Integer(), nullable=False), sa.Column("stripe_price_id", sa.String(length=100), nullable=True), sa.Column("paypal_plan_id", sa.String(length=100), nullable=True), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table("subscriptions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), nullable=False), sa.Column("plan_id", sa.Integer(), nullable=False), sa.Column("provider", sa.String(length=20), nullable=False), sa.Column("provider_subscription_id", sa.String(length=255), nullable=False), sa.Column("provider_customer_id", sa.String(length=255), nullable=True), sa.Column("status", sa.Enum("incomplete", "trialing", "active", "past_due", "canceled", name="subscriptionstatus"), nullable=False), sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]), sa.UniqueConstraint("user_id", name="uq_subscriptions_user_id"))
    plans_table = sa.table("plans", sa.column("name", sa.String), sa.column("price_cents", sa.Integer), sa.column("currency", sa.String), sa.column("interval", sa.String), sa.column("daily_ai_request_limit", sa.Integer), sa.column("is_active", sa.Boolean))
    op.bulk_insert(plans_table, [{"name":"Free","price_cents":0,"currency":"usd","interval":"month","daily_ai_request_limit":20,"is_active":True},{"name":"Pro","price_cents":1900,"currency":"usd","interval":"month","daily_ai_request_limit":500,"is_active":True}])

def downgrade() -> None:
    op.drop_table("subscriptions"); op.drop_table("plans"); sa.Enum(name="subscriptionstatus").drop(op.get_bind(), checkfirst=True)
