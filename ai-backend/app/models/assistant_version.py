"""نسخ تاريخية من إعدادات المساعد المخصص."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class AssistantVersion(Base):
    __tablename__ = "assistant_versions"
    __table_args__ = (
        UniqueConstraint(
            "assistant_id",
            "version",
            name="uq_assistant_versions_assistant_version",
        ),
        Index(
            "ix_assistant_versions_assistant_id_created_at",
            "assistant_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assistant_id: Mapped[int] = mapped_column(
        ForeignKey("assistants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    assistant = relationship("Assistant", back_populates="versions")
