from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SavedPromptVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    name: str
    content: str
    created_at: datetime


class SavedPromptVersionCompareOut(BaseModel):
    from_version: int
    current_version: int
    diff: str
    changed: bool
