"""مسارات المشاريع داخل مساحات العمل."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.conversation import Conversation
from app.models.project import WorkspaceProject
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.projects import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["Workspace Projects"])


def _get_membership(workspace_id: int, current_user: User, db: Session) -> WorkspaceMember:
    membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مساحة العمل غير موجودة",
        )
    return membership


def _get_project(project_id: int, current_user: User, db: Session) -> WorkspaceProject:
    project = db.get(WorkspaceProject, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المشروع غير موجود",
        )
    _get_membership(project.workspace_id, current_user, db)
    return project


def _ensure_unique_name(
    workspace_id: int,
    name: str,
    db: Session,
    exclude_id: int | None = None,
) -> None:
    normalized = name.strip().lower()
    query = db.query(WorkspaceProject).filter(
        WorkspaceProject.workspace_id == workspace_id,
        func.lower(WorkspaceProject.name) == normalized,
    )
    if exclude_id is not None:
        query = query.filter(WorkspaceProject.id != exclude_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="يوجد مشروع بهذا الاسم في مساحة العمل",
        )


def _can_manage(project: WorkspaceProject, membership: WorkspaceMember) -> None:
    if membership.role not in {WorkspaceRole.owner, WorkspaceRole.admin}:
        # منشئ المشروع يستطيع إدارة مشروعه.
        if project.owner_id != membership.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="هذه العملية تتطلب صلاحية مدير المشروع أو مساحة العمل",
            )


@router.get("", response_model=list[ProjectOut])
def list_projects(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_membership(workspace_id, current_user, db)
    return (
        db.query(WorkspaceProject)
        .filter(WorkspaceProject.workspace_id == workspace_id)
        .order_by(WorkspaceProject.created_at.asc(), WorkspaceProject.id.asc())
        .all()
    )


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_membership(payload.workspace_id, current_user, db)
    _ensure_unique_name(payload.workspace_id, payload.name, db)

    project = WorkspaceProject(
        workspace_id=payload.workspace_id,
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description.strip() if payload.description else None,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, current_user, db)
    membership = _get_membership(project.workspace_id, current_user, db)
    _can_manage(project, membership)
    _ensure_unique_name(project.workspace_id, payload.name, db, exclude_id=project.id)

    project.name = payload.name
    project.description = payload.description.strip() if payload.description else None
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, current_user, db)
    membership = _get_membership(project.workspace_id, current_user, db)
    _can_manage(project, membership)

    db.query(Conversation).filter(
        Conversation.project_id == project.id
    ).update({"project_id": None}, synchronize_session=False)
    db.delete(project)
    db.commit()
