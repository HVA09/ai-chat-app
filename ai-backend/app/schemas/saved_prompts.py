from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SavedPromptCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=8000)

    @field_validator("name", "content")
    @classmethod
    def values_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("القيمة لا يمكن أن تكون فارغة")
        return v


class SavedPromptUpdate(SavedPromptCreate):
    pass


class SavedPromptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    content: str
    created_at: datetime
    updated_at: datetime
