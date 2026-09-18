from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.workspace import WorkspaceRole


class WorkspaceInviteCreate(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.member

    @field_validator("role")
    @classmethod
    def role_must_not_be_owner(cls, v: WorkspaceRole) -> WorkspaceRole:
        if v == WorkspaceRole.owner:
            raise ValueError("لا يمكن دعوة مستخدم بدور المالك")
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: EmailStr) -> str:
        return str(v).strip().lower()


class WorkspaceMemberOut(BaseModel):
    id: int
    user_id: int
    email: EmailStr
    full_name: str | None = None
    role: WorkspaceRole
    created_at: datetime


class WorkspaceInvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: WorkspaceRole
    created_at: datetime
    expires_at: datetime


class WorkspaceRoleUpdate(BaseModel):
    role: WorkspaceRole

    @field_validator("role")
    @classmethod
    def role_must_not_be_owner(cls, v: WorkspaceRole) -> WorkspaceRole:
        if v == WorkspaceRole.owner:
            raise ValueError("لا يمكن تعيين دور المالك عبر هذا المسار")
        return v


class WorkspaceInvitationAccept(BaseModel):
    token: str = Field(min_length=20, max_length=256)


class WorkspaceInvitationAcceptOut(BaseModel):
    workspace_id: int
    workspace_name: str
    role: WorkspaceRole
