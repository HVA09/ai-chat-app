"""إدارة الذاكرة المشتركة الخاصة بمشاريع مساحة العمل."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.project import WorkspaceProject
from app.models.project_memory import ProjectMemory
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.project_memories import (
    ProjectMemoryCreate,
    ProjectMemoryOut,
    ProjectMemoryUpdate,
)

router = APIRouter(prefix="/projects/{project_id}/memories", tags=["Project Memories"])


def _get_project_and_membership(
    project_id: int, current_user: User, db: Session
) -> tuple[WorkspaceProject, WorkspaceMember]:
    project = db.get(WorkspaceProject, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المشروع غير موجود",
        )

    membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == project.workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المشروع غير موجود",
        )
    return project, membership


def _ensure_can_manage_memory(
    project: WorkspaceProject, membership: WorkspaceMember
) -> None:
    if membership.role in {WorkspaceRole.owner, WorkspaceRole.admin}:
        return
    if project.owner_id == membership.user_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="إدارة ذاكرة المشروع تتطلب صلاحية مدير المشروع أو مساحة العمل",
    )


def _get_memory(
    project_id: int, memory_id: int, current_user: User, db: Session
) -> tuple[ProjectMemory, WorkspaceProject, WorkspaceMember]:
    project, membership = _get_project_and_membership(project_id, current_user, db)
    memory = (
        db.query(ProjectMemory)
        .filter(
            ProjectMemory.id == memory_id,
            ProjectMemory.project_id == project.id,
        )
        .first()
    )
    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ذاكرة المشروع غير موجودة",
        )
    return memory, project, membership


@router.get("", response_model=list[ProjectMemoryOut])
def list_project_memories(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_project_and_membership(project_id, current_user, db)
    return (
        db.query(ProjectMemory)
        .filter(ProjectMemory.project_id == project_id)
        .order_by(ProjectMemory.updated_at.desc(), ProjectMemory.id.desc())
        .limit(50)
        .all()
    )


@router.post("", response_model=ProjectMemoryOut, status_code=status.HTTP_201_CREATED)
def create_project_memory(
    project_id: int,
    payload: ProjectMemoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project, membership = _get_project_and_membership(project_id, current_user, db)
    _ensure_can_manage_memory(project, membership)

    memory_count = (
        db.query(ProjectMemory)
        .filter(ProjectMemory.project_id == project.id)
        .count()
    )
    if memory_count >= 50:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="وصل المشروع إلى الحد الأقصى من الذكريات",
        )

    memory = ProjectMemory(
        project_id=project.id,
        created_by_user_id=current_user.id,
        content=payload.content,
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


@router.patch("/{memory_id}", response_model=ProjectMemoryOut)
def update_project_memory(
    project_id: int,
    memory_id: int,
    payload: ProjectMemoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memory, project, membership = _get_memory(project_id, memory_id, current_user, db)
    _ensure_can_manage_memory(project, membership)
    memory.content = payload.content
    db.commit()
    db.refresh(memory)
    return memory


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_memory(
    project_id: int,
    memory_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memory, project, membership = _get_memory(project_id, memory_id, current_user, db)
    _ensure_can_manage_memory(project, membership)
    db.delete(memory)
    db.commit()
