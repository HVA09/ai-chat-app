from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.project_member import ProjectMemberRole


class ProjectMemberCreate(BaseModel):
    user_id: int
    role: ProjectMemberRole = ProjectMemberRole.viewer


class ProjectMemberUpdate(BaseModel):
    role: ProjectMemberRole


class ProjectMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None
    project_id: int
    user_id: int
    email: str
    full_name: str | None
    role: ProjectMemberRole
    created_at: datetime
    is_owner: bool = False
