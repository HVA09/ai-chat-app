from datetime import datetime

from pydantic import BaseModel


class WorkspaceAuditLogOut(BaseModel):
    id: int
    user_id: int | None
    actor_email: str | None
    event_type: str
    description: str
    created_at: datetime
