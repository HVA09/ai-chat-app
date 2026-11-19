"""Preserve original-uploader privacy when a project/workspace scope is removed."""

from sqlalchemy import or_
from sqlalchemy.orm import Session, load_only

from app.models.assistant import Assistant
from app.models.assistant_file_link import AssistantFileLink
from app.models.audit_log import AuditLog
from app.models.assistant_version import AssistantVersion
from app.models.file_attachment import FileAttachment
from app.models.project import WorkspaceProject
from app.models.workspace import Workspace
from app.models.user import User


def lock_user_for_update(db: Session, user_id: int) -> None:
    """Serialize project creation with deletion of the owning account."""
    db.query(User.id).filter(User.id == user_id).with_for_update().first()


def lock_workspaces_for_update(db: Session, workspace_ids: list[int]) -> None:
    """Serialize file-scope changes with uploads and assistant-version restores."""
    unique_ids = sorted({int(workspace_id) for workspace_id in workspace_ids})
    if not unique_ids:
        return
    (
        db.query(Workspace.id)
        .filter(Workspace.id.in_(unique_ids))
        .order_by(Workspace.id.asc())
        .with_for_update()
        .all()
    )


def _privatize_attachment_ids(db: Session, file_ids: list[int]) -> None:
    """Detach files from shared scopes and invalidate historical assistant links."""
    if not file_ids:
        return

    target_ids = set(file_ids)
    # Snapshot creation/update takes the assistant row lock before reading live
    # links. Lock every assistant currently linked to these files first so a
    # concurrent snapshot either commits before this scan or observes links
    # after they have been removed. Assistant IDs are always locked in order.
    assistant_ids = [
        assistant_id
        for (assistant_id,) in db.query(AssistantFileLink.assistant_id)
        .filter(AssistantFileLink.file_id.in_(file_ids))
        .distinct()
        .order_by(AssistantFileLink.assistant_id.asc())
        .all()
    ]
    if assistant_ids:
        (
            db.query(Assistant.id)
            .filter(Assistant.id.in_(assistant_ids))
            .order_by(Assistant.id.asc())
            .with_for_update()
            .all()
        )
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
        # Restore locks the selected snapshot row. Retention must take the same
        # row lock (after workspace locks) before scrubbing it, even when the
        # assistant is shared only to a different workspace. This closes the
        # stale-snapshot race independently of the assistant's current shares.
        .order_by(AssistantVersion.id.asc())
        .with_for_update()
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

    # Keep the same row-lock order as assistant-version restore:
    # workspace rows (held by the caller), then Assistant rows, then
    # AssistantVersion rows, then AssistantFileLink rows. Deleting links before locking snapshots can
    # deadlock with restore, which locks a snapshot before replacing links.
    db.query(AssistantFileLink).filter(
        AssistantFileLink.file_id.in_(file_ids)
    ).delete(synchronize_session=False)

    db.query(FileAttachment).filter(
        FileAttachment.id.in_(file_ids)
    ).update(
        {"workspace_id": None, "project_id": None},
        synchronize_session=False,
    )


def privatize_project_attachments(db: Session, project_id: int) -> list[int]:
    """Move all uploads in a deleted project to each original uploader's scope."""
    project_scope = (
        db.query(WorkspaceProject.workspace_id)
        .filter(WorkspaceProject.id == project_id)
        .first()
    )
    if project_scope is None:
        return []
    lock_workspaces_for_update(db, [project_scope.workspace_id])
    # Re-read after acquiring the workspace lock. An upload that completed
    # first is included; an upload arriving later must revalidate and fail.
    project_scope = (
        db.query(WorkspaceProject.workspace_id)
        .populate_existing()
        .filter(WorkspaceProject.id == project_id)
        .first()
    )
    if project_scope is None:
        return []
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
    # Project creation/import takes this same user-row lock before workspace
    # locks. This prevents a new owned project in somebody else's workspace
    # from appearing after the account-deletion inventory was collected.
    lock_user_for_update(db, user_id)
    workspace_ids = [
        workspace_id
        for (workspace_id,) in db.query(Workspace.id)
        .filter(Workspace.owner_id == user_id)
        .order_by(Workspace.id.asc())
        .all()
    ]
    owned_project_workspace_ids = [
        workspace_id
        for (workspace_id,) in db.query(WorkspaceProject.workspace_id)
        .filter(WorkspaceProject.owner_id == user_id)
        .distinct()
        .order_by(WorkspaceProject.workspace_id.asc())
        .all()
    ]
    # A user can own projects inside somebody else's workspace. Lock those
    # workspace rows too, otherwise their uploads could race with account
    # deletion even though the user's own workspaces are protected.
    lock_workspaces_for_update(
        db,
        workspace_ids + owned_project_workspace_ids,
    )

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
