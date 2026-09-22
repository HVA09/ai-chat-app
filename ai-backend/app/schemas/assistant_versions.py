from datetime import datetime

from pydantic import BaseModel


class AssistantVersionOut(BaseModel):
    id: int
    version: int
    name: str
    description: str | None
    instructions: str
    created_at: datetime
