"""مسارات إنشاء وإدارة مجلدات المحادثات."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.conversation import Conversation
from app.models.conversation_folder import ConversationFolder
from app.models.user import User
from app.schemas.folders import FolderCreate, FolderOut, FolderRename

router = APIRouter(prefix="/folders", tags=["Conversation Folders"])


def _get_owned_folder(folder_id: int, current_user: User, db: Session) -> ConversationFolder:
    folder = (
        db.query(ConversationFolder)
        .filter(
            ConversationFolder.id == folder_id,
            ConversationFolder.user_id == current_user.id,
        )
        .first()
    )
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المجلد غير موجود",
        )
    return folder


def _ensure_unique_name(name: str, current_user: User, db: Session, exclude_id: int | None = None) -> None:
    query = db.query(ConversationFolder).filter(
        ConversationFolder.user_id == current_user.id,
        func.lower(ConversationFolder.name) == name.lower(),
    )
    if exclude_id is not None:
        query = query.filter(ConversationFolder.id != exclude_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="يوجد مجلد بهذا الاسم",
        )


@router.get("", response_model=list[FolderOut])
def list_folders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(ConversationFolder)
        .filter(ConversationFolder.user_id == current_user.id)
        .order_by(ConversationFolder.created_at.asc(), ConversationFolder.id.asc())
        .all()
    )


@router.post("", response_model=FolderOut, status_code=status.HTTP_201_CREATED)
def create_folder(
    payload: FolderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_unique_name(payload.name, current_user, db)
    folder = ConversationFolder(user_id=current_user.id, name=payload.name)
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
    folder = _get_owned_folder(folder_id, current_user, db)
    _ensure_unique_name(payload.name, current_user, db, exclude_id=folder.id)
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
    folder = _get_owned_folder(folder_id, current_user, db)
    # المحادثات لا تُحذف عند حذف المجلد؛ تصبح غير مصنفة فقط.
    db.query(Conversation).filter(Conversation.folder_id == folder.id).update(
        {Conversation.folder_id: None}, synchronize_session=False
    )
    db.delete(folder)
    db.commit()
