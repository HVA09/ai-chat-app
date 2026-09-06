"""
تتبع استخدام الـ AI لكل مستخدم — يُستخدم للحد اليومي (Authorization)
ولاستعلامات SQL/التقارير لاحقًا.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class UsageLog(Base):
    __tablename__ = "usage_logs"
    __table_args__ = (
        # يخدم enforce_daily_ai_limit — يشتغل على كل طلب /chat، أهم استعلام بالنظام أداءً
        Index("ix_usage_logs_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="usage_logs")
