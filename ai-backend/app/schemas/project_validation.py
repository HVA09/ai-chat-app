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
