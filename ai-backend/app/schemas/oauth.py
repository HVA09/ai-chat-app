from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OAuthProviderOut(BaseModel):
    provider: str


class OAuthStartOut(BaseModel):
    provider: str
    authorization_url: str
    expires_at: datetime


class OAuthConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    subject: str
    email: str | None
    scopes: list[str]
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OAuthCallbackOut(BaseModel):
    provider: str
    connection_id: int
    email: str | None
