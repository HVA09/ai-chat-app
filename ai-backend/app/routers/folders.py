"""مسارات إنشاء وإدارة مجلدات المحادثات الشخصية ومساحات العمل."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.conversation import Conversation
from app.models.conversation_folder import ConversationFolder
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.folders import FolderCreate, FolderOut, FolderRename

router = APIRouter(prefix="/folders", tags=["Conversation Folders"])


def _get_workspace_membership(
    workspace_id: int, current_user: User, db: Session
) -> WorkspaceMember:
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


def _get_accessible_folder(
    folder_id: int, current_user: User, db: Session
) -> ConversationFolder:
    folder = db.get(ConversationFolder, folder_id)
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المجلد غير موجود",
        )

    if folder.workspace_id is None:
        if folder.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المجلد غير موجود",
            )
        return folder

    _get_workspace_membership(folder.workspace_id, current_user, db)
    return folder


def _ensure_unique_name(
    name: str,
    current_user: User,
    db: Session,
    workspace_id: int | None,
    exclude_id: int | None = None,
) -> None:
    normalized = name.strip().lower()
    query = db.query(ConversationFolder).filter(
        func.lower(ConversationFolder.name) == normalized
    )

    if workspace_id is None:
        query = query.filter(
            ConversationFolder.user_id == current_user.id,
            ConversationFolder.workspace_id.is_(None),
        )
    else:
        query = query.filter(ConversationFolder.workspace_id == workspace_id)

    if exclude_id is not None:
        query = query.filter(ConversationFolder.id != exclude_id)

    if query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="يوجد مجلد بهذا الاسم",
        )


def _can_manage_folder(
    folder: ConversationFolder, current_user: User, db: Session
) -> None:
    if folder.workspace_id is None:
        if folder.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المجلد غير موجود",
            )
        return

    membership = _get_workspace_membership(folder.workspace_id, current_user, db)
    if membership.role not in {WorkspaceRole.owner, WorkspaceRole.admin}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذه العملية تتطلب صلاحية مدير مساحة العمل",
        )


@router.get("", response_model=list[FolderOut])
def list_folders(
    workspace_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if workspace_id is None:
        query = db.query(ConversationFolder).filter(
            ConversationFolder.user_id == current_user.id,
            ConversationFolder.workspace_id.is_(None),
        )
    else:
        _get_workspace_membership(workspace_id, current_user, db)
        query = db.query(ConversationFolder).filter(
            or_(
                ConversationFolder.workspace_id.is_(None)
                & (ConversationFolder.user_id == current_user.id),
                ConversationFolder.workspace_id == workspace_id,
            )
        )

    return (
        query
        .order_by(ConversationFolder.created_at.asc(), ConversationFolder.id.asc())
        .all()
    )


@router.post("", response_model=FolderOut, status_code=status.HTTP_201_CREATED)
def create_folder(
    payload: FolderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.workspace_id is not None:
        _get_workspace_membership(payload.workspace_id, current_user, db)

    _ensure_unique_name(payload.name, current_user, db, payload.workspace_id)

    folder = ConversationFolder(
        user_id=current_user.id,
        workspace_id=payload.workspace_id,
        name=payload.name,
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


@router.patch("/{folder_id}", response_model=FolderOut)
def rename_folder(
    folder_id: int,
    payload: FolderRename,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    folder = _get_accessible_folder(folder_id, current_user, db)
    _can_manage_folder(folder, current_user, db)
    _ensure_unique_name(
        payload.name,
        current_user,
        db,
        folder.workspace_id,
        exclude_id=folder.id,
    )
    folder.name = payload.name
    db.commit()
    db.refresh(folder)
    return folder


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(
    folder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    folder = _get_accessible_folder(folder_id, current_user, db)
    _can_manage_folder(folder, current_user, db)

    db.query(Conversation).filter(Conversation.folder_id == folder.id).update(
        {Conversation.folder_id: None}, synchronize_session=False
    )
    db.delete(folder)
    db.commit()
