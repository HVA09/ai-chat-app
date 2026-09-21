from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.conversation import MessageRole
from app.schemas.tags import TagOut


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: int | None = None
    assistant_id: int | None = None
    workspace_id: int | None = None
    model: str | None = Field(default=None, max_length=100)

    @field_validator("model")
    @classmethod
    def model_name_normalize(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

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
    is_bookmarked: bool = False


class VisionResponse(BaseModel):
    conversation_id: int
    reply: str


class ChatModelOut(BaseModel):
    id: str
    label: str
    is_default: bool


class ChatResponse(BaseModel):
    conversation_id: int
    reply: str
    sources: list[dict[str, Any]] = Field(default_factory=list)


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    is_pinned: bool
    is_archived: bool
    folder_id: int | None
    project_id: int | None
    assistant_id: int | None
    workspace_id: int
    ai_model: str | None
    deleted_at: datetime | None
    tags: list[TagOut] = Field(default_factory=list)
    parent_conversation_id: int | None
    branched_from_message_index: int | None


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]
    summary: str | None
    summary_updated_at: datetime | None


class ConversationSummaryOut(BaseModel):
    conversation_id: int
    summary: str
    summary_updated_at: datetime


class ConversationRename(BaseModel):
    title: str = Field(min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("العنوان لا يمكن أن يكون فارغًا")
        return v


class ConversationBulkExportRequest(BaseModel):
    conversation_ids: list[int] = Field(min_length=1, max_length=50)

    @field_validator("conversation_ids")
    @classmethod
    def unique_conversation_ids(cls, v: list[int]) -> list[int]:
        unique = list(dict.fromkeys(v))
        if not unique:
            raise ValueError("يجب اختيار محادثة واحدة على الأقل")
        return unique


class ConversationImportMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)
    sources: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("content")
    @classmethod
    def imported_content_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("محتوى الرسالة لا يمكن أن يكون فارغًا")
        return v


class ConversationImportRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    messages: list[ConversationImportMessage] = Field(min_length=1, max_length=500)
    folder_id: int | None = None
    project_id: int | None = None
    assistant_id: int | None = None
    ai_model: str | None = Field(default=None, max_length=100)

    @field_validator("title")
    @classmethod
    def imported_title_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("عنوان المحادثة لا يمكن أن يكون فارغًا")
        return v

    @field_validator("messages")
    @classmethod
    def imported_messages_size(cls, v: list[ConversationImportMessage]) -> list[ConversationImportMessage]:
        total_chars = sum(len(message.content) for message in v)
        if total_chars > 200_000:
            raise ValueError("حجم المحادثة المستوردة كبير جدًا")
        return v


class ConversationBulkImportRequest(BaseModel):
    version: Literal[1] = 1
    conversations: list[ConversationImportRequest] = Field(min_length=1, max_length=50)

    @field_validator("conversations")
    @classmethod
    def bulk_size_limits(
        cls, v: list[ConversationImportRequest]
    ) -> list[ConversationImportRequest]:
        total_messages = sum(len(item.messages) for item in v)
        total_chars = sum(
            len(message.content) for item in v for message in item.messages
        )
        if total_messages > 5000:
            raise ValueError("عدد الرسائل المستوردة كبير جدًا")
        if total_chars > 2_000_000:
            raise ValueError("حجم المحادثات المستوردة كبير جدًا")
        return v


class ConversationBulkImportOut(BaseModel):
    conversation_ids: list[int]
    imported_count: int


