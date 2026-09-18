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
