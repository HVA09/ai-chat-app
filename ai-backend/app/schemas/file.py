from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    is_attached: bool = False
    workspace_id: int | None = None
    project_id: int | None = None
    is_owner: bool = False
    can_delete: bool = False
    is_ai_indexed: bool = False
