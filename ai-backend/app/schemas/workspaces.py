from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.workspace import WorkspaceRole


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("اسم مساحة العمل لا يمكن أن يكون فارغًا")
        return v


class WorkspaceRename(WorkspaceCreate):
    pass


class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    role: WorkspaceRole
    default_ai_model: str | None
    daily_ai_request_limit: int | None
    created_at: datetime


class WorkspaceDefaultModelUpdate(BaseModel):
    model: str | None = Field(default=None, max_length=100)

    @field_validator("model")
    @classmethod
    def normalize_model(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class WorkspaceDailyLimitUpdate(BaseModel):
    daily_ai_request_limit: int | None = Field(default=None, ge=1, le=100000)
