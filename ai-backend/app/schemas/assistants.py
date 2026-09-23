from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AssistantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=300)
    instructions: str = Field(min_length=1, max_length=6000)

    @field_validator("name", "instructions")
    @classmethod
    def required_text_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("القيمة لا يمكن أن تكون فارغة")
        return v

    @field_validator("description")
    @classmethod
    def normalize_description(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class AssistantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=300)
    instructions: str | None = Field(default=None, min_length=1, max_length=6000)

    @field_validator("name", "instructions")
    @classmethod
    def optional_text_not_blank(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("القيمة لا يمكن أن تكون فارغة")
        return v

    @field_validator("description")
    @classmethod
    def normalize_description(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class AssistantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    instructions: str
    created_at: datetime
    is_public: bool


class AssistantPublicSettingsUpdate(BaseModel):
    rotate: bool = False


class AssistantPublicSettingsOut(BaseModel):
    is_public: bool
    public_token: str | None
    public_url: str | None


class AssistantAnalyticsOut(BaseModel):
    assistant_id: int
    days: int
    conversation_count: int
    message_count: int
    active_user_count: int
    last_used_at: datetime | None
