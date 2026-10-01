"""إدارة شجرة ملفات المصدر النصية داخل مشاريع مساحة العمل."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.project import WorkspaceProject
from app.models.project_file import ProjectFile
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.project_files import (
    ProjectFileCreate,
    ProjectFileOut,
    ProjectFileSummaryOut,
    ProjectFileUpdate,
)

router = APIRouter(prefix="/projects/{project_id}/files", tags=["Project Files"])

MAX_PROJECT_FILES = 200


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


def _ensure_can_manage(
    project: WorkspaceProject, membership: WorkspaceMember
) -> None:
    if membership.role in {WorkspaceRole.owner, WorkspaceRole.admin}:
        return
    if project.owner_id == membership.user_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="تعديل ملفات المشروع يتطلب صلاحية مدير المشروع أو مساحة العمل",
    )


def _get_file(
    project_id: int,
    file_id: int,
    current_user: User,
    db: Session,
) -> tuple[ProjectFile, WorkspaceProject, WorkspaceMember]:
    project, membership = _get_project_and_membership(project_id, current_user, db)
    project_file = (
        db.query(ProjectFile)
        .filter(
            ProjectFile.id == file_id,
            ProjectFile.project_id == project.id,
        )
        .first()
    )
    if not project_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ملف المشروع غير موجود",
        )
    return project_file, project, membership


@router.get("", response_model=list[ProjectFileSummaryOut])
def list_project_files(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project, _ = _get_project_and_membership(project_id, current_user, db)
    files = (
        db.query(ProjectFile)
        .filter(ProjectFile.project_id == project.id)
        .order_by(ProjectFile.path.asc(), ProjectFile.id.asc())
        .all()
    )
    return [
        {
            "id": item.id,
            "project_id": item.project_id,
            "path": item.path,
            "content_length": len(item.content),
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
        for item in files
    ]


@router.get("/{file_id}", response_model=ProjectFileOut)
def get_project_file(
    project_id: int,
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project_file, _, _ = _get_file(project_id, file_id, current_user, db)
    return project_file


@router.post("", response_model=ProjectFileOut, status_code=status.HTTP_201_CREATED)
def create_project_file(
    project_id: int,
    payload: ProjectFileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project, membership = _get_project_and_membership(project_id, current_user, db)
    _ensure_can_manage(project, membership)

    count = db.query(ProjectFile).filter(ProjectFile.project_id == project.id).count()
    if count >= MAX_PROJECT_FILES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="وصل المشروع إلى الحد الأقصى من 200 ملف مصدر",
        )

    project_file = ProjectFile(
        project_id=project.id,
        path=payload.path,
        content=payload.content,
    )
    try:
        with db.begin_nested():
            db.add(project_file)
            db.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="يوجد ملف بهذا المسار داخل المشروع",
        ) from exc
    db.commit()
    db.refresh(project_file)
    return project_file


@router.patch("/{file_id}", response_model=ProjectFileOut)
def update_project_file(
    project_id: int,
    file_id: int,
    payload: ProjectFileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project_file, project, membership = _get_file(
        project_id, file_id, current_user, db
    )
    _ensure_can_manage(project, membership)

    try:
        with db.begin_nested():
            project_file.path = payload.path
            project_file.content = payload.content
            db.flush()
    except IntegrityError as exc:
        db.expire(project_file)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="يوجد ملف آخر بهذا المسار داخل المشروع",
        ) from exc
    db.commit()
    db.refresh(project_file)
    return project_file


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_file(
    project_id: int,
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project_file, project, membership = _get_file(
        project_id, file_id, current_user, db
    )
    _ensure_can_manage(project, membership)
    db.delete(project_file)
    db.commit()
