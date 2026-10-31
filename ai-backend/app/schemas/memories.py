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



class MemorySuggestionsRequest(BaseModel):
    conversation_id: int = Field(gt=0)


class MemorySuggestion(BaseModel):
    content: str = Field(min_length=1, max_length=300)
    evidence: str = Field(min_length=1, max_length=250)

    @field_validator("content", "evidence")
    @classmethod
    def normalize_suggestion_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("النص لا يمكن أن يكون فارغًا")
        return normalized


class MemorySuggestionsOut(BaseModel):
    conversation_id: int
    suggestions: list[MemorySuggestion] = Field(default_factory=list)
