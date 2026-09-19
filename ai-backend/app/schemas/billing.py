from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.subscription import SubscriptionStatus


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price_cents: int
    currency: str
    interval: str
    daily_ai_request_limit: int


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan: PlanOut
    provider: str
    status: SubscriptionStatus
    current_period_end: datetime | None


class UsageOut(BaseModel):
    window_hours: int
    window_start: datetime
    used_requests: int
    daily_limit: int | None
    remaining_requests: int | None
    input_tokens: int
    output_tokens: int
    total_tokens: int


class CheckoutRequest(BaseModel):
    plan_id: int


class CheckoutResponse(BaseModel):
    checkout_url: str
