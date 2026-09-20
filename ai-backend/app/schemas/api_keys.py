from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class APIKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("اسم المفتاح لا يمكن أن يكون فارغًا")
        return v


class APIKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    key_prefix: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class APIKeyCreatedOut(APIKeyOut):
    secret: str


class APIChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: int | None = None
    workspace_id: int | None = None
    assistant_id: int | None = None
    model: str | None = Field(default=None, max_length=100)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("الرسالة لا يمكن أن تكون فارغة")
        return v

    @field_validator("model")
    @classmethod
    def model_name_normalize(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class APIChatResponse(BaseModel):
    conversation_id: int
    reply: str
    model: str


class APIKeyUsageOut(BaseModel):
    key_id: int
    window_hours: int
    used_requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
