from datetime import datetime

from pydantic import BaseModel


class WorkspaceUsageMemberOut(BaseModel):
    user_id: int
    email: str
    full_name: str | None
    used_requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int


class WorkspaceUsageOut(BaseModel):
    workspace_id: int
    window_hours: int
    window_start: datetime
    used_requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    month_start: datetime
    monthly_budget_usd: float | None
    month_spent_usd: float
    monthly_budget_remaining_usd: float | None
    pricing_configured: bool
    members: list[WorkspaceUsageMemberOut]
