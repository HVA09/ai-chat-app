from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_path(value: str) -> str:
    value = value.replace("\\", "/").strip()
    if not value or "\u0000" in value:
        raise ValueError("مسار الملف غير صالح")
    if value.startswith("/") or any(part == ".." for part in value.split("/")):
        raise ValueError("مسار الملف غير آمن")
    normalized = "/".join(part for part in value.split("/") if part not in {"", "."})
    if not normalized:
        raise ValueError("مسار الملف غير صالح")
    return normalized


class ProjectFileCreate(BaseModel):
    path: str = Field(min_length=1, max_length=512)
    content: str = Field(max_length=50_000)

    @field_validator("path")
    @classmethod
    def path_is_safe(cls, value: str) -> str:
        return _normalize_path(value)


class ProjectFileUpdate(ProjectFileCreate):
    pass


class ProjectFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    path: str
    content: str
    created_at: datetime
    updated_at: datetime
