from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScheduledTaskRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scheduled_task_id: int
    workspace_id: int
    prompt: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    conversation_id: int | None
    error: str | None
    created_at: datetime
