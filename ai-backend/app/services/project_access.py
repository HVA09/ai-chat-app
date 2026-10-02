"""Project-level access policy layered on top of workspace membership."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.project import WorkspaceProject
from app.models.project_member import ProjectMember, ProjectMemberRole
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.services.workspace_rbac import has_workspace_permission


def get_workspace_membership(
    project: WorkspaceProject,
    current_user: User,
    db: Session,
) -> WorkspaceMember | None:
    return (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == project.workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
        .first()
    )


def get_project_member(
    project: WorkspaceProject,
    current_user: User,
    db: Session,
) -> ProjectMember | None:
    return (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == current_user.id,
        )
        .first()
    )


def effective_project_role(
    project: WorkspaceProject,
    current_user: User,
    db: Session,
) -> ProjectMemberRole | None:
    if project.owner_id == current_user.id:
        return None

    membership = get_workspace_membership(project, current_user, db)
    if membership is None:
        return None

    if has_workspace_permission(db, membership, "projects.manage"):
        return ProjectMemberRole.manager

    member = get_project_member(project, current_user, db)
    return member.role if member else None


def can_read_project(
    project: WorkspaceProject,
    current_user: User,
    db: Session,
) -> bool:
    return project.owner_id == current_user.id or effective_project_role(project, current_user, db) is not None


def can_edit_project(
    project: WorkspaceProject,
    current_user: User,
    db: Session,
) -> bool:
    if project.owner_id == current_user.id:
        return True
    role = effective_project_role(project, current_user, db)
    return role in {ProjectMemberRole.editor, ProjectMemberRole.manager}


def can_manage_project(
    project: WorkspaceProject,
    current_user: User,
    db: Session,
) -> bool:
    if project.owner_id == current_user.id:
        return True
    role = effective_project_role(project, current_user, db)
    return role == ProjectMemberRole.manager
