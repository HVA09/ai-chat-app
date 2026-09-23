from datetime import datetime

from pydantic import BaseModel


class SessionOut(BaseModel):
    id: int
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    user_agent: str | None
    ip_address: str | None
    is_current: bool
