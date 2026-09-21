from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScheduledTaskCreate(BaseModel):
    workspace_id: int
    prompt: str = Field(min_length=1, max_length=4000)
    schedule_type: Literal["once", "daily", "weekly"]
    next_run_at: datetime
    weekday: int | None = Field(default=None, ge=0, le=6)

    @field_validator("prompt")
    @classmethod
    def prompt_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("الموجه لا يمكن أن يكون فارغًا")
        return v

    @field_validator("next_run_at")
    @classmethod
    def next_run_must_have_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("وقت التنفيذ يجب أن يتضمن منطقة زمنية")
        return v

    @field_validator("weekday")
    @classmethod
    def weekday_is_required_for_weekly(cls, v: int | None, info):
        schedule_type = info.data.get("schedule_type")
        if schedule_type == "weekly" and v is None:
            raise ValueError("يجب تحديد يوم الأسبوع للمهمة الأسبوعية")
        return v


class ScheduledTaskUpdate(BaseModel):
    prompt: str | None = Field(default=None, min_length=1, max_length=4000)
    schedule_type: Literal["once", "daily", "weekly"] | None = None
    next_run_at: datetime | None = None
    weekday: int | None = Field(default=None, ge=0, le=6)
    is_active: bool | None = None

    @field_validator("prompt")
    @classmethod
    def update_prompt_not_blank(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("الموجه لا يمكن أن يكون فارغًا")
        return v

    @field_validator("next_run_at")
    @classmethod
    def update_run_must_have_timezone(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("وقت التنفيذ يجب أن يتضمن منطقة زمنية")
        return v


class ScheduledTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    prompt: str
    schedule_type: str
    next_run_at: datetime
    weekday: int | None
    is_active: bool
    last_run_at: datetime | None
    last_error: str | None
    created_at: datetime
