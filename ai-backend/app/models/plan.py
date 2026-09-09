"""
خطط الاشتراك — كل خطة مرتبطة بحد يومي لطلبات AI (Authorization) ومعرّف السعر
عند كل مزوّد دفع (Stripe/PayPal)
"""
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="usd", nullable=False)
    interval: Mapped[str] = mapped_column(String(20), default="month", nullable=False)  # month|year
    daily_ai_request_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    stripe_price_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    paypal_plan_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
