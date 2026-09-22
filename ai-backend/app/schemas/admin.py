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


class ProviderUsageStat(BaseModel):
    provider: str
    requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int


class ProviderLatencyStat(BaseModel):
    provider: str
    requests: int
    avg_latency_ms: int
    min_latency_ms: int
    max_latency_ms: int


class ModelUsageStat(BaseModel):
    model: str
    requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int


class CostBudgetStatus(BaseModel):
    month_start: str
    budget_usd: float | None
    spent_usd: float
    remaining_usd: float | None
    usage_percent: float | None
    over_budget: bool
    pricing_configured: bool
    unpriced_requests: int


class FeedbackAnalytics(BaseModel):
    days: int
    total_rated: int
    positive: int
    negative: int
    positive_rate: float | None


class CostUsageStat(BaseModel):
    provider: str
    model: str
    requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost_usd: float | None
    output_cost_usd: float | None
    total_cost_usd: float | None
    pricing_configured: bool


class AdminPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price_cents: int
    currency: str
    interval: str
    daily_ai_request_limit: int
    allowed_models: list[str]
    is_active: bool


class AdminPlanUpdate(BaseModel):
    daily_ai_request_limit: int | None = None
    allowed_models: list[str] | None = None
    is_active: bool | None = None
