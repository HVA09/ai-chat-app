"""
اشتراك المستخدم — وحدة واحدة لكل مستخدم، تدعم Stripe أو PayPal
"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class SubscriptionStatus(str, enum.Enum):
    incomplete = "incomplete"
    trialing = "trialing"
    active = "active"
    past_due = "past_due"
    canceled = "canceled"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)  # stripe | paypal
    provider_subscription_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.incomplete, nullable=False
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    plan = relationship("Plan")
