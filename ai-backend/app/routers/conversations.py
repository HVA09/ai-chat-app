"""
مسارات إدارة محادثات المستخدم الحالي: عرض، تعديل الاسم، حذف
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.assistant import Assistant
from app.models.conversation import Conversation
from app.models.conversation_folder import ConversationFolder
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.chat import ConversationDetail, ConversationOut, ConversationRename
from app.schemas.folders import ConversationFolderUpdate


router = APIRouter(prefix="/conversations", tags=["Conversations"])


def _get_owned_conversation(conversation_id: int, current_user: User, db: Session) -> Conversation:
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المحادثة غير موجودة")
    return conversation


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
    folder_id: int | None = None,
    assistant_id: int | None = None,
    workspace_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    limit = min(max(limit, 1), 100)
    skip = max(skip, 0)

    query = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_archived == include_archived,
    )

    if workspace_id is not None:
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
        query = query.filter(Conversation.workspace_id == workspace_id)

    if folder_id is not None:
        owned_folder = (
            db.query(ConversationFolder)
            .filter(
                ConversationFolder.id == folder_id,
                ConversationFolder.user_id == current_user.id,
            )
            .first()
        )
        if not owned_folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المجلد غير موجود",
            )
        query = query.filter(Conversation.folder_id == folder_id)

    if assistant_id is not None:
        owned_assistant = (
            db.query(Assistant)
            .filter(
                Assistant.id == assistant_id,
                Assistant.user_id == current_user.id,
            )
            .first()
        )
        if not owned_assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المساعد غير موجود",
            )
        query = query.filter(Conversation.assistant_id == assistant_id)

    return (
        query
        .order_by(Conversation.is_pinned.desc(), Conversation.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .options(selectinload(Conversation.messages))
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المحادثة غير موجودة")
    return conversation


@router.patch("/{conversation_id}", response_model=ConversationOut)
def rename_conversation(
    conversation_id: int,
    payload: ConversationRename,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned_conversation(conversation_id, current_user, db)
    conversation.title = payload.title
    db.commit()
    db.refresh(conversation)
    return conversation


@router.patch("/{conversation_id}/pin", response_model=ConversationOut)
def toggle_pin_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned_conversation(conversation_id, current_user, db)
    conversation.is_pinned = not conversation.is_pinned
    db.commit()
    db.refresh(conversation)
    return conversation


@router.patch("/{conversation_id}/archive", response_model=ConversationOut)
def toggle_archive_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned_conversation(conversation_id, current_user, db)
    conversation.is_archived = not conversation.is_archived
    db.commit()
    db.refresh(conversation)
    return conversation


@router.patch("/{conversation_id}/folder", response_model=ConversationOut)
def set_conversation_folder(
    conversation_id: int,
    payload: ConversationFolderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned_conversation(conversation_id, current_user, db)

    if payload.folder_id is not None:
        owned_folder = (
            db.query(ConversationFolder)
            .filter(
                ConversationFolder.id == payload.folder_id,
                ConversationFolder.user_id == current_user.id,
            )
            .first()
        )
        if not owned_folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المجلد غير موجود",
            )

    conversation.folder_id = payload.folder_id
    db.commit()
    db.refresh(conversation)
    return conversation


@router.patch("/{conversation_id}/assistant", response_model=ConversationOut)
def set_conversation_assistant(
    conversation_id: int,
    assistant_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned_conversation(conversation_id, current_user, db)
    if assistant_id is not None:
        owned_assistant = (
            db.query(Assistant)
            .filter(
                Assistant.id == assistant_id,
                Assistant.user_id == current_user.id,
            )
            .first()
        )
        if not owned_assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المساعد غير موجود",
            )
    conversation.assistant_id = assistant_id
    db.commit()
    db.refresh(conversation)
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned_conversation(conversation_id, current_user, db)
    db.delete(conversation)
    db.commit()
