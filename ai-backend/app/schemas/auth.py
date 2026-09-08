from pydantic import BaseModel, EmailStr, Field, field_validator
from app.validators import normalize_email, validate_strong_password


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None

    @field_validator("email")
    @classmethod
    def email_normalize(cls, v: str) -> str:
        return normalize_email(v)


class Token(BaseModel):
    # Authentication tokens are delivered only as HttpOnly cookies.
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    pass


class EmailVerificationConfirm(BaseModel):
    token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def email_normalize(cls, v: str) -> str:
        return normalize_email(v)


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_strong_password(v)


class TwoFactorSetupResponse(BaseModel):
    secret: str
    qr_code_base64: str


class TwoFactorCodeRequest(BaseModel):
    totp_code: str = Field(min_length=6, max_length=6)
