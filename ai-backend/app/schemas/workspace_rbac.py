from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WorkspaceRBACPermissionCatalogItem(BaseModel):
    permission: str
    description: str


class WorkspaceRBACRoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=300)
    permissions: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("اسم الدور مطلوب")
        return value


class WorkspaceRBACRoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=300)
    permissions: list[str] | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("اسم الدور مطلوب")
        return value


class WorkspaceRBACRoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    name: str
    description: str | None
    is_system: bool
    permissions: list[str]
    created_at: datetime
    updated_at: datetime


class WorkspaceMemberRBACRoleUpdate(BaseModel):
    rbac_role_id: int | None = None
