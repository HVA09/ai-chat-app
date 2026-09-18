"""مسارات مساحة العمل الحالية للمستخدم."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.schemas.workspaces import WorkspaceCreate, WorkspaceOut, WorkspaceRename

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


def _get_membership(
    workspace_id: int, current_user: User, db: Session
) -> WorkspaceMember:
    membership = (
        db.query(WorkspaceMember)
        .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
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


def _ensure_unique_owned_name(
    name: str, owner_id: int, db: Session, exclude_id: int | None = None
) -> None:
    query = db.query(Workspace).filter(
        Workspace.owner_id == owner_id,
        func.lower(Workspace.name) == func.lower(name.strip()),
    )
    if exclude_id is not None:
        query = query.filter(Workspace.id != exclude_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="لديك مساحة عمل بهذا الاسم",
        )


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .filter(WorkspaceMember.user_id == current_user.id)
        .order_by(Workspace.created_at.asc(), Workspace.id.asc())
        .all()
    )
    return [
        WorkspaceOut(
            id=workspace.id,
            name=workspace.name,
            role=role,
            created_at=workspace.created_at,
        )
        for workspace, role in rows
    ]


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_unique_owned_name(payload.name, current_user.id, db)
    workspace = Workspace(owner_id=current_user.id, name=payload.name)
    db.add(workspace)
    db.flush()
    db.add(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=current_user.id,
            role=WorkspaceRole.owner,
        )
    )
    db.commit()
    db.refresh(workspace)
    return WorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        role=WorkspaceRole.owner,
        created_at=workspace.created_at,
    )


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
def rename_workspace(
    workspace_id: int,
    payload: WorkspaceRename,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = _get_membership(workspace_id, current_user, db)
    if membership.role not in {WorkspaceRole.owner, WorkspaceRole.admin}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذه العملية تتطلب صلاحية مدير مساحة العمل",
        )

    workspace = membership.workspace
    _ensure_unique_owned_name(
        payload.name,
        workspace.owner_id,
        db,
        exclude_id=workspace.id,
    )
    workspace.name = payload.name
    db.commit()
    db.refresh(workspace)
    return WorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        role=membership.role,
        created_at=workspace.created_at,
    )
