from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


WebhookEventType = Literal[
    "api_key.created",
    "api_key.revoked",
    "webhook.test",
]


def _validate_events(events: list[str]) -> list[str]:
    allowed = {"api_key.created", "api_key.revoked", "webhook.test"}
    values = [str(item).strip() for item in events]
    if not values or len(values) > 10 or any(item not in allowed for item in values):
        raise ValueError("event_types contains an unsupported webhook event")
    if len(set(values)) != len(values):
        raise ValueError("event_types must not contain duplicates")
    return values


class WebhookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1, max_length=2048)
    event_types: list[WebhookEventType] = Field(min_length=1, max_length=10)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("الاسم لا يمكن أن يكون فارغًا")
        return value

    @field_validator("url")
    @classmethod
    def normalize_url(cls, value: str) -> str:
        return value.strip()

    @field_validator("event_types")
    @classmethod
    def validate_event_types(cls, value):
        return _validate_events(value)


class WebhookUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    event_types: list[WebhookEventType] | None = Field(default=None, min_length=1, max_length=10)
    is_active: bool | None = None
    rotate_secret: bool = False

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("الاسم لا يمكن أن يكون فارغًا")
        return value

    @field_validator("url")
    @classmethod
    def normalize_url(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("event_types")
    @classmethod
    def validate_event_types(cls, value):
        return _validate_events(value) if value is not None else None


class WebhookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    event_types: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WebhookCreatedOut(WebhookOut):
    secret: str


class WebhookUpdateOut(WebhookOut):
    secret: str | None = None


class WebhookDeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    event_type: str
    status: str
    attempt_count: int
    response_status: int | None
    last_error: str | None
    next_attempt_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
