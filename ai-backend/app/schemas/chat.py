from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.conversation import MessageRole


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: int | None = None
    assistant_id: int | None = None
    workspace_id: int | None = None

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("الرسالة لا يمكن أن تكون فارغة")
        return v


class VisionRequest(BaseModel):
    conversation_id: int
    file_id: int
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def vision_message_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("سؤال الصورة لا يمكن أن يكون فارغًا")
        return v


class ChatEditRequest(BaseModel):
    message_index: int = Field(ge=1)
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("الرسالة لا يمكن أن تكون فارغة")
        return v


class MessageFeedbackRequest(BaseModel):
    rating: Literal[-1, 1] | None = None


class MessageFeedbackOut(BaseModel):
    message_index: int
    feedback: int | None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: MessageRole
    content: str
    created_at: datetime
    sources: list[dict[str, Any]] | None = None
    feedback: int | None = None


class VisionResponse(BaseModel):
    conversation_id: int
    reply: str


class ChatResponse(BaseModel):
    conversation_id: int
    reply: str
    sources: list[dict[str, Any]] = Field(default_factory=list)


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    is_pinned: bool
    is_archived: bool
    folder_id: int | None
    assistant_id: int | None
    workspace_id: int


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]


class ConversationRename(BaseModel):
    title: str = Field(min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("العنوان لا يمكن أن يكون فارغًا")
        return v
