"""Preserve original-uploader privacy when a project/workspace scope is removed."""

from sqlalchemy import or_
from sqlalchemy.orm import Session, load_only

from app.models.assistant_file_link import AssistantFileLink
from app.models.audit_log import AuditLog
from app.models.assistant_version import AssistantVersion
from app.models.file_attachment import FileAttachment
from app.models.project import WorkspaceProject
from app.models.workspace import Workspace


def _privatize_attachment_ids(db: Session, file_ids: list[int]) -> None:
    """Detach files from shared scopes and invalidate historical assistant links."""
    if not file_ids:
        return

    db.query(AssistantFileLink).filter(
        AssistantFileLink.file_id.in_(file_ids)
    ).delete(synchronize_session=False)

    target_ids = set(file_ids)
    # Stream only the two fields needed; never materialize unrelated assistant
    # instructions/tool policies or the full version history during deletion.
    snapshots = (
        db.query(AssistantVersion)
        .options(
            load_only(
                AssistantVersion.id,
                AssistantVersion.knowledge_file_ids,
            )
        )
        .filter(AssistantVersion.knowledge_file_ids.is_not(None))
        .yield_per(200)
    )
    for snapshot in snapshots:
        saved_ids = snapshot.knowledge_file_ids
        if not isinstance(saved_ids, list):
            continue
        filtered_ids = [
            file_id
            for file_id in saved_ids
            if not (
                str(file_id).isdigit()
                and int(file_id) in target_ids
            )
        ]
        if len(filtered_ids) != len(saved_ids):
            # Reassign rather than mutating JSON in place so SQLAlchemy detects it.
            snapshot.knowledge_file_ids = filtered_ids

    db.query(FileAttachment).filter(
        FileAttachment.id.in_(file_ids)
    ).update(
        {"workspace_id": None, "project_id": None},
        synchronize_session=False,
    )


def privatize_project_attachments(db: Session, project_id: int) -> list[int]:
    """Move all uploads in a deleted project to each original uploader's scope."""
    file_ids = [
        file_id
        for (file_id,) in db.query(FileAttachment.id)
        .filter(FileAttachment.project_id == project_id)
        .all()
    ]
    _privatize_attachment_ids(db, file_ids)
    return file_ids


def privatize_account_workspace_attachments(db: Session, user_id: int) -> list[int]:
    """Protect other members' uploads when an account deletion cascades workspaces/projects."""
    workspace_ids = [
        workspace_id
        for (workspace_id,) in db.query(Workspace.id)
        .filter(Workspace.owner_id == user_id)
        .all()
    ]

    # Preserve audit history but detach references to workspaces that are about
    # to disappear in the account-delete cascade.
    if workspace_ids:
        db.query(AuditLog).filter(
            AuditLog.workspace_id.in_(workspace_ids)
        ).update(
            {AuditLog.workspace_id: None},
            # Keep already-loaded AuditLog ORM instances in sync. Account deletion
            # may flush them again when their user_id is nulled by ORM cascades.
            synchronize_session="fetch",
        )

    project_query = db.query(WorkspaceProject.id).filter(
        WorkspaceProject.owner_id == user_id
    )
    if workspace_ids:
        project_query = project_query.union(
            db.query(WorkspaceProject.id).filter(
                WorkspaceProject.workspace_id.in_(workspace_ids)
            )
        )
    project_ids = [project_id for (project_id,) in project_query.all()]

    scope_filters = []
    if project_ids:
        scope_filters.append(FileAttachment.project_id.in_(project_ids))
    if workspace_ids:
        scope_filters.append(FileAttachment.workspace_id.in_(workspace_ids))
    if not scope_filters:
        return []

    file_ids = [
        file_id
        for (file_id,) in db.query(FileAttachment.id)
        .filter(or_(*scope_filters))
        .all()
    ]
    _privatize_attachment_ids(db, file_ids)
    return file_ids
