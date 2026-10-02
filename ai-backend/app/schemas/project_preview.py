from pydantic import BaseModel, Field


class PreviewBuildFile(BaseModel):
    path: str
    content: str


class PreviewBuildRequest(BaseModel):
    project_id: int
    project_kind: str
    files: list[PreviewBuildFile]
    build_command: str = "npm run build"


class PreviewBuildResponse(BaseModel):
    entrypoint: str
    artifact_base64: str
    artifact_size_bytes: int = Field(ge=0)
    preview_url: str | None = None
    preview_expires_at: int | None = Field(default=None, ge=0)
