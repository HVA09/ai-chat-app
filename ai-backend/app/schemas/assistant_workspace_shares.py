from datetime import datetime

from pydantic import BaseModel


class AssistantWorkspaceShareOut(BaseModel):
    id: int
    assistant_id: int
    workspace_id: int
    shared_by_user_id: int
    shared_by_email: str
    created_at: datetime


class WorkspaceSharedAssistantOut(BaseModel):
    id: int
    name: str
    description: str | None
    owner_user_id: int
    owner_email: str
    workspace_id: int
    shared_at: datetime
    is_shared: bool = True
    can_edit: bool = False
