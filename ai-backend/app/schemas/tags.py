from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


HEX_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(default="#64748B", pattern=HEX_COLOR_PATTERN)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("اسم الوسم لا يمكن أن يكون فارغًا")
        return v


class TagRename(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(default="#64748B", pattern=HEX_COLOR_PATTERN)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("اسم الوسم لا يمكن أن يكون فارغًا")
        return v


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str
    created_at: datetime


class ConversationTagsUpdate(BaseModel):
    tag_ids: list[int] = Field(default_factory=list, max_length=10)
