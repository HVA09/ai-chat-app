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


class CheckoutRequest(BaseModel):
    plan_id: int


class CheckoutResponse(BaseModel):
    checkout_url: str
