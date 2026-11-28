"""Immutable identity for the storage backend that owns uploaded objects."""
from datetime import datetime
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base

class StorageProfile(Base):
    __tablename__ = "storage_profiles"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    bucket: Mapped[str | None] = mapped_column(String(255), nullable=True)
    endpoint_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    root_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    credential_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
