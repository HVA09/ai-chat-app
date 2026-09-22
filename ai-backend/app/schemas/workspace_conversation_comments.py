from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConversationCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    message_id: int | None = None

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("التعليق لا يمكن أن يكون فارغًا")
        return v


class ConversationCommentUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("التعليق لا يمكن أن يكون فارغًا")
        return v


class ConversationCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    user_id: int
    user_email: str
    message_id: int | None
    content: str
    created_at: datetime
    updated_at: datetime
