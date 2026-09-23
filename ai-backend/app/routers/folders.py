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
from app.schemas.folders import FolderCreate, FolderMoveRequest, FolderOut, FolderRename

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


def _folder_scope_filter(current_user: User, workspace_id: int | None):
    if workspace_id is None:
        return (
            ConversationFolder.user_id == current_user.id,
            ConversationFolder.workspace_id.is_(None),
        )
    return (ConversationFolder.workspace_id == workspace_id,)


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
    if (
        membership.role not in {WorkspaceRole.owner, WorkspaceRole.admin}
        and folder.user_id != current_user.id
    ):
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
        .order_by(
            ConversationFolder.workspace_id.is_not(None).asc(),
            ConversationFolder.sort_order.asc(),
            ConversationFolder.created_at.asc(),
            ConversationFolder.id.asc(),
        )
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

    scope_filters = _folder_scope_filter(current_user, payload.workspace_id)
    max_sort_order = (
        db.query(func.max(ConversationFolder.sort_order))
        .filter(*scope_filters)
        .scalar()
    )

    folder = ConversationFolder(
        user_id=current_user.id,
        workspace_id=payload.workspace_id,
        name=payload.name,
        color=payload.color,
        sort_order=(max_sort_order + 1) if max_sort_order is not None else 0,
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
    if payload.color is not None:
        folder.color = payload.color
    db.commit()
    db.refresh(folder)
    return folder


@router.patch("/{folder_id}/position", response_model=FolderOut)
def move_folder_position(
    folder_id: int,
    payload: FolderMoveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    folder = _get_accessible_folder(folder_id, current_user, db)
    _can_manage_folder(folder, current_user, db)

    scope_filters = _folder_scope_filter(current_user, folder.workspace_id)
    siblings = (
        db.query(ConversationFolder)
        .filter(*scope_filters)
        .order_by(
            ConversationFolder.sort_order.asc(),
            ConversationFolder.created_at.asc(),
            ConversationFolder.id.asc(),
        )
        .all()
    )

    index = next((i for i, item in enumerate(siblings) if item.id == folder.id), None)
    if index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المجلد غير موجود",
        )

    target_index = index - 1 if payload.direction == "up" else index + 1
    if target_index < 0 or target_index >= len(siblings):
        db.refresh(folder)
        return folder

    target = siblings[target_index]
    folder.sort_order, target.sort_order = target.sort_order, folder.sort_order
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
