"""مشاركة المحادثات للقراءة فقط داخل مساحة العمل."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.conversation import Conversation
from app.models.conversation_workspace_share import ConversationWorkspaceShare
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.schemas.workspace_conversation_shares import (
    WorkspaceConversationShareOut,
    WorkspaceSharedConversationDetail,
    WorkspaceSharedConversationOut,
)

router = APIRouter(tags=["Workspace Conversation Sharing"])


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
        raise HTTPException(status_code=404, detail="مساحة العمل غير موجودة")
    return membership


def _get_owned_conversation(conversation_id: int, current_user: User, db: Session) -> Conversation:
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
            Conversation.deleted_at.is_(None),
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="المحادثة غير موجودة")
    return conversation


@router.get(
    "/conversations/{conversation_id}/workspace-share",
    response_model=WorkspaceConversationShareOut,
)
def get_conversation_workspace_share(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned_conversation(conversation_id, current_user, db)
    share = (
        db.query(ConversationWorkspaceShare, User)
        .join(User, User.id == ConversationWorkspaceShare.shared_by_user_id)
        .filter(ConversationWorkspaceShare.conversation_id == conversation.id)
        .first()
    )
    if not share:
        raise HTTPException(status_code=404, detail="المحادثة غير مشتركة مع مساحة العمل")
    share_row, shared_by = share
    return WorkspaceConversationShareOut(
        id=share_row.id,
        conversation_id=share_row.conversation_id,
        workspace_id=share_row.workspace_id,
        created_at=share_row.created_at,
        shared_by_user_id=share_row.shared_by_user_id,
        shared_by_email=shared_by.email,
    )


@router.post(
    "/conversations/{conversation_id}/workspace-share",
    response_model=WorkspaceConversationShareOut,
    status_code=status.HTTP_201_CREATED,
)
def share_conversation_with_workspace(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned_conversation(conversation_id, current_user, db)
    if not conversation.workspace_id:
        raise HTTPException(
            status_code=400,
            detail="هذه المحادثة غير مرتبطة بمساحة عمل",
        )

    _get_membership(conversation.workspace_id, current_user, db)

    existing = (
        db.query(ConversationWorkspaceShare)
        .filter(ConversationWorkspaceShare.conversation_id == conversation.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="المحادثة مشتركة بالفعل")

    share = ConversationWorkspaceShare(
        conversation_id=conversation.id,
        workspace_id=conversation.workspace_id,
        shared_by_user_id=current_user.id,
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return WorkspaceConversationShareOut(
        id=share.id,
        conversation_id=share.conversation_id,
        workspace_id=share.workspace_id,
        created_at=share.created_at,
        shared_by_user_id=share.shared_by_user_id,
        shared_by_email=current_user.email,
    )


@router.delete(
    "/conversations/{conversation_id}/workspace-share",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unshare_conversation_from_workspace(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned_conversation(conversation_id, current_user, db)
    share = (
        db.query(ConversationWorkspaceShare)
        .filter(ConversationWorkspaceShare.conversation_id == conversation.id)
        .first()
    )
    if not share:
        raise HTTPException(status_code=404, detail="المشاركة غير موجودة")
    db.delete(share)
    db.commit()


@router.get(
    "/workspaces/{workspace_id}/shared-conversations",
    response_model=list[WorkspaceSharedConversationOut],
)
def list_workspace_shared_conversations(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_membership(workspace_id, current_user, db)
    rows = (
        db.query(
            ConversationWorkspaceShare,
            Conversation,
            User,
        )
        .join(Conversation, Conversation.id == ConversationWorkspaceShare.conversation_id)
        .join(User, User.id == Conversation.user_id)
        .filter(
            ConversationWorkspaceShare.workspace_id == workspace_id,
            Conversation.deleted_at.is_(None),
        )
        .order_by(ConversationWorkspaceShare.created_at.desc())
        .limit(100)
        .all()
    )
    shared_by_users = {
        user_id: email
        for user_id, email in db.query(User.id, User.email).filter(
            User.id.in_({share.shared_by_user_id for share, _, _ in rows})
        ).all()
    }
    return [
        WorkspaceSharedConversationOut(
            conversation_id=conversation.id,
            workspace_id=workspace_id,
            title=conversation.title,
            updated_at=conversation.updated_at,
            owner_email=owner.email,
            shared_by_email=shared_by_users.get(share.shared_by_user_id, owner.email),
            shared_at=share.created_at,
        )
        for share, conversation, owner in rows
    ]


@router.get(
    "/workspaces/{workspace_id}/shared-conversations/{conversation_id}",
    response_model=WorkspaceSharedConversationDetail,
)
def get_workspace_shared_conversation(
    workspace_id: int,
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_membership(workspace_id, current_user, db)
    row = (
        db.query(ConversationWorkspaceShare, Conversation, User)
        .join(Conversation, Conversation.id == ConversationWorkspaceShare.conversation_id)
        .join(User, User.id == Conversation.user_id)
        .filter(
            ConversationWorkspaceShare.workspace_id == workspace_id,
            ConversationWorkspaceShare.conversation_id == conversation_id,
            Conversation.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="المحادثة المشتركة غير موجودة")

    share, conversation, owner = row
    messages = [
        {
            "role": message.role.value,
            "content": message.content,
            "created_at": message.created_at,
            "sources": message.sources or [],
        }
        for message in sorted(conversation.messages, key=lambda item: (item.created_at, item.id))
    ]
    return WorkspaceSharedConversationDetail(
        conversation_id=conversation.id,
        workspace_id=workspace_id,
        title=conversation.title,
        updated_at=conversation.updated_at,
        owner_email=owner.email,
        messages=messages,
    )
