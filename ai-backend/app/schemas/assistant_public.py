from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssistantPublicSettingsOut(BaseModel):
    is_public: bool
    public_token: str | None
    public_url: str | None


class AssistantPublicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    description: str | None
    created_at: datetime


class AssistantPublicDuplicateOut(BaseModel):
    conversation_assistant_id: int
    name: str
