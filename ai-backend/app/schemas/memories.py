from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("الذاكرة لا يمكن أن تكون فارغة")
        return value


class MemoryUpdate(MemoryCreate):
    pass


class MemoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    created_at: datetime
    updated_at: datetime
