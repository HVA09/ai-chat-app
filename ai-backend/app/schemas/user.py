from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator

from app.models.user import UserRole
from app.validators import normalize_email, validate_strong_password


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_strong_password(v)

    @field_validator("email")
    @classmethod
    def email_normalize(cls, v: str) -> str:
        return normalize_email(v)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    is_email_verified: bool
    is_2fa_enabled: bool
    full_name: str | None
    avatar_url: str | None
    created_at: datetime


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=500)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_strong_password(v)


class DeleteAccountRequest(BaseModel):
    password: str
