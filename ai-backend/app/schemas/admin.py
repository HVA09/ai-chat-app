from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    is_email_verified: bool
    created_at: datetime


class AdminUserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class AdminConversationOut(BaseModel):
    id: int
    user_id: int
    user_email: str
    title: str
    created_at: datetime


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    event_type: str
    description: str
    created_at: datetime


class AdminStats(BaseModel):
    total_users: int
    total_conversations: int
    total_messages: int
    total_ai_requests: int
    total_files: int
    storage_used_bytes: int


class DailyStatsPoint(BaseModel):
    date: str
    new_users: int
    new_conversations: int
    ai_requests: int
    input_tokens: int
    output_tokens: int
