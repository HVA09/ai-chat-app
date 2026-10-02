from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


PROJECT_ARCHIVE_SCHEMA_VERSION = 1
ProjectImportConflict = Literal["fail", "rename"]


class ProjectArchiveFile(BaseModel):
    path: str = Field(min_length=1, max_length=512)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_size: int = Field(ge=0, le=50_000)


class ProjectArchiveMemory(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


class ProjectArchiveManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    project: dict
    files: list[ProjectArchiveFile] = Field(max_length=200)
    memories: list[ProjectArchiveMemory] = Field(max_length=50)

    @field_validator("project")
    @classmethod
    def project_is_object(cls, value: dict) -> dict:
        allowed = {"name", "description", "instructions"}
        unknown = set(value).difference(allowed)
        if unknown:
            raise ValueError("manifest يحتوي حقول مشروع غير مدعومة")
        name = str(value.get("name", "")).strip()
        if not name or len(name) > 120:
            raise ValueError("اسم المشروع داخل manifest غير صالح")
        description = value.get("description")
        instructions = value.get("instructions")
        if description is not None and len(str(description)) > 1000:
            raise ValueError("وصف المشروع يتجاوز الحد")
        if instructions is not None and len(str(instructions)) > 6000:
            raise ValueError("تعليمات المشروع تتجاوز الحد")
        value["name"] = name
        value["description"] = str(description).strip() if description else None
        value["instructions"] = str(instructions).strip() if instructions else None
        return value


class ProjectImportResult(BaseModel):
    project_id: int
    workspace_id: int
    name: str
    files_imported: int
    memories_imported: int
    conflict_policy: ProjectImportConflict
