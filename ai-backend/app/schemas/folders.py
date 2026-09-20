from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    workspace_id: int | None = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("اسم المجلد لا يمكن أن يكون فارغًا")
        return v


class FolderRename(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("اسم المجلد لا يمكن أن يكون فارغًا")
        return v


class FolderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    workspace_id: int | None
    created_at: datetime


class ConversationFolderUpdate(BaseModel):
    folder_id: int | None = None
