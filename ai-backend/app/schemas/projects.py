from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectCreate(BaseModel):
    workspace_id: int
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    instructions: str | None = Field(default=None, max_length=6000)
    assistant_id: int | None = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("اسم المشروع لا يمكن أن يكون فارغًا")
        return v


class ProjectUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    instructions: str | None = Field(default=None, max_length=6000)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("اسم المشروع لا يمكن أن يكون فارغًا")
        return v


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    owner_id: int
    name: str
    description: str | None
    instructions: str | None
    assistant_id: int | None
    created_at: datetime


class ConversationProjectUpdate(BaseModel):
    project_id: int | None = None
