"""Persistent lifecycle and cleanup helpers for project preview artifacts."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models.project_preview_artifact import ProjectPreviewArtifact
from app.services.project_preview_artifacts import _object_key, PublishedPreview
from app.services.storage import StorageError, delete_file


ACTIVE = "active"
SUPERSEDED = "superseded"


def register_preview_artifact(
    db: Session,
    project_id: int,
    published: PublishedPreview,
    size_bytes: int,
    file_paths: list[str],
) -> None:
    now = datetime.now(timezone.utc)
    existing = (
        db.query(ProjectPreviewArtifact)
        .filter(
            ProjectPreviewArtifact.project_id == project_id,
            ProjectPreviewArtifact.artifact_id == published.artifact_id,
        )
        .first()
    )

    superseded = (
        db.query(ProjectPreviewArtifact)
        .filter(
            ProjectPreviewArtifact.project_id == project_id,
            ProjectPreviewArtifact.status == ACTIVE,
            ProjectPreviewArtifact.artifact_id != published.artifact_id,
        )
        .all()
    )
    for artifact in superseded:
        artifact.status = SUPERSEDED

    artifact_root = (
        published.entrypoint.rsplit("/", 1)[0]
        if "/" in published.entrypoint
        else ""
    )
    if existing is None:
        existing = ProjectPreviewArtifact(
            project_id=project_id,
            artifact_id=published.artifact_id,
            entrypoint=published.entrypoint,
            artifact_root=artifact_root,
            size_bytes=size_bytes,
            file_count=len(file_paths),
            files_manifest=sorted(file_paths),
            status=ACTIVE,
            expires_at=datetime.fromtimestamp(published.expires_at, tz=timezone.utc),
        )
        db.add(existing)
    else:
        existing.entrypoint = published.entrypoint
        existing.artifact_root = artifact_root
        existing.size_bytes = size_bytes
        existing.file_count = len(file_paths)
        existing.files_manifest = sorted(file_paths)
        existing.status = ACTIVE
        existing.expires_at = datetime.fromtimestamp(
            published.expires_at,
            tz=timezone.utc,
        )

    db.commit()

    for artifact in superseded:
        cleanup_preview_artifact_objects(artifact.project_id, artifact)


def cleanup_preview_artifact_objects(
    project_id: int,
    artifact: ProjectPreviewArtifact,
) -> None:
    errors: list[str] = []
    for path in artifact.files_manifest or []:
        try:
            delete_file(
                _object_key(project_id, artifact.artifact_id, path),
                Path(settings.UPLOAD_DIR) / _object_key(
                    project_id,
                    artifact.artifact_id,
                    path,
                ),
            )
        except StorageError as exc:
            errors.append(str(exc))
    if errors:
        # Cleanup is best-effort after lifecycle state is persisted.
        return


def delete_preview_artifact(
    db: Session,
    artifact: ProjectPreviewArtifact,
) -> None:
    cleanup_preview_artifact_objects(artifact.project_id, artifact)
    db.delete(artifact)
    db.commit()
