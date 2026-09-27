"""Historical versions of a saved prompt."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class SavedPromptVersion(Base):
    __tablename__ = "saved_prompt_versions"
    __table_args__ = (
        UniqueConstraint(
            "saved_prompt_id",
            "version",
            name="uq_saved_prompt_versions_prompt_version",
        ),
        Index(
            "ix_saved_prompt_versions_prompt_created_at",
            "saved_prompt_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    saved_prompt_id: Mapped[int] = mapped_column(
        ForeignKey("saved_prompts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    saved_prompt = relationship("SavedPrompt", back_populates="versions")
