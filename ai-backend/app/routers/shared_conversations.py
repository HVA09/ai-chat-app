"""Public read-only conversation sharing."""
from datetime import datetime, timezone
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.conversation import Conversation
from app.models.conversation_share import ConversationShare
from app.models.user import User
from app.schemas.chat import ConversationDetail
from app.schemas.shares import (
    ConversationShareCreate,
    ConversationShareManageOut,
    ConversationShareOut,
    SharedConversationOut,
    SharedMessageOut,
)

router = APIRouter(tags=["Conversation Sharing"])


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _share_url(token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/share/{token}"


def _get_owned_conversation(
    conversation_id: int, current_user: User, db: Session
) -> Conversation:
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المحادثة غير موجودة",
        )
    return conversation


@router.post(
    "/conversations/{conversation_id}/share",
    response_model=ConversationShareOut,
)
def create_conversation_share(
    conversation_id: int,
    payload: ConversationShareCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned_conversation(conversation_id, current_user, db)

    token = secrets.token_urlsafe(32)
    expires_at = None
    if payload.expires_in_days is not None:
        expires_at = datetime.now(timezone.utc).replace(microsecond=0)
        from datetime import timedelta
        expires_at = expires_at + timedelta(days=payload.expires_in_days)

    share = ConversationShare(
        conversation_id=conversation.id,
        token_hash=_hash_token(token),
        expires_at=expires_at,
    )
    db.add(share)
    db.commit()
    db.refresh(share)

    return ConversationShareOut(
        id=share.id,
        url=_share_url(token),
        created_at=share.created_at,
        expires_at=share.expires_at,
    )


@router.get(
    "/conversations/{conversation_id}/shares",
    response_model=list[ConversationShareManageOut],
)
def list_conversation_shares(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned_conversation(conversation_id, current_user, db)
    now = datetime.now(timezone.utc)
    shares = (
        db.query(ConversationShare)
        .filter(ConversationShare.conversation_id == conversation.id)
        .order_by(ConversationShare.created_at.desc(), ConversationShare.id.desc())
        .all()
    )
    return [
        ConversationShareManageOut(
            id=share.id,
            created_at=share.created_at,
            expires_at=share.expires_at,
            is_expired=share.expires_at is not None and share.expires_at <= now,
        )
        for share in shares
    ]


@router.delete(
    "/conversations/{conversation_id}/share/{share_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_conversation_share(
    conversation_id: int,
    share_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_conversation(conversation_id, current_user, db)
    share = (
        db.query(ConversationShare)
        .filter(
            ConversationShare.id == share_id,
            ConversationShare.conversation_id == conversation_id,
        )
        .first()
    )
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="رابط المشاركة غير موجود",
        )
    db.delete(share)
    db.commit()


@router.get(
    "/shared-conversations/{token}",
    response_model=SharedConversationOut,
)
def get_shared_conversation(
    token: str,
    db: Session = Depends(get_db),
):
    if not token or len(token) > 256:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="رابط المشاركة غير صالح",
        )

    share = (
        db.query(ConversationShare)
        .options(selectinload(ConversationShare.conversation).selectinload(Conversation.messages))
        .filter(ConversationShare.token_hash == _hash_token(token))
        .first()
    )

    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="رابط المشاركة غير موجود",
        )

    now = datetime.now(timezone.utc)
    if share.expires_at is not None and share.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="انتهت صلاحية رابط المشاركة",
        )

    conversation = share.conversation
    return SharedConversationOut(
        title=conversation.title,
        created_at=conversation.created_at,
        expires_at=share.expires_at,
        messages=[
            SharedMessageOut(
                role=message.role.value,
                content=message.content,
                created_at=message.created_at,
                sources=message.sources,
            )
            for message in conversation.messages
        ],
    )
