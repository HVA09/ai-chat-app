from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    artifact_id: str
    entrypoint: str
    artifact_size_bytes: int = Field(ge=0)
    expires_at: int = Field(ge=0)
    created_at: datetime


class ProjectArtifactCleanupResult(BaseModel):
    removed: int = Field(ge=0)
    remaining: int = Field(ge=0)
