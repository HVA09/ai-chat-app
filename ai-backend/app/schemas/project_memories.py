from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectMemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("ذاكرة المشروع لا يمكن أن تكون فارغة")
        return value


class ProjectMemoryUpdate(ProjectMemoryCreate):
    pass


class ProjectMemoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    created_by_user_id: int
    content: str
    created_at: datetime
    updated_at: datetime
