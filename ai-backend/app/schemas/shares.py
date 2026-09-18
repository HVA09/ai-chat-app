from datetime import datetime

from pydantic import BaseModel, Field


class ConversationShareCreate(BaseModel):
    # None = no expiry; otherwise 1–30 days.
    expires_in_days: int | None = Field(default=7, ge=1, le=30)


class ConversationShareOut(BaseModel):
    id: int
    url: str
    created_at: datetime
    expires_at: datetime | None


class SharedMessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime
    sources: list[dict] | None = None


class SharedConversationOut(BaseModel):
    title: str
    created_at: datetime
    expires_at: datetime | None
    messages: list[SharedMessageOut]
