from pydantic import BaseModel


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
