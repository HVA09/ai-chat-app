from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ProjectPreviewArtifactOut(BaseModel):
    id: int
    project_id: int
    artifact_id: str
    entrypoint: str
    artifact_root: str
    size_bytes: int = Field(ge=0)
    file_count: int = Field(ge=0)
    status: Literal["active", "superseded", "expired"]
    expires_at: datetime
    created_at: datetime
