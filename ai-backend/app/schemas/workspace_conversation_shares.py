from datetime import datetime

from pydantic import BaseModel


class WorkspaceConversationShareOut(BaseModel):
    id: int
    conversation_id: int
    workspace_id: int
    created_at: datetime
    shared_by_user_id: int
    shared_by_email: str


class WorkspaceSharedConversationOut(BaseModel):
    conversation_id: int
    workspace_id: int
    title: str
    updated_at: datetime
    owner_email: str
    shared_by_email: str
    shared_at: datetime


class WorkspaceSharedConversationDetail(BaseModel):
    conversation_id: int
    workspace_id: int
    title: str
    updated_at: datetime
    owner_email: str
    messages: list[dict]
