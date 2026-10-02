from pydantic import BaseModel


class ProjectValidationItem(BaseModel):
    level: str
    code: str
    message: str
    path: str | None = None


class ProjectValidationOut(BaseModel):
    project_id: int
    project_kind: str
    files_count: int
    errors: int
    warnings: int
    checks: list[ProjectValidationItem]


class ProjectPreviewPlanOut(BaseModel):
    project_id: int
    project_kind: str
    strategy: str
    status: str
    entrypoint: str | None = None
    build_command_detected: bool = False
    artifact_root: str | None = None
    message: str
