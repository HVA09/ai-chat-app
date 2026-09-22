from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssistantVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    name: str
    description: str | None
    instructions: str
    created_at: datetime
