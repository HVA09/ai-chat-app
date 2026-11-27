"""Public read-only conversation sharing."""
from datetime import datetime, timezone
import hashlib
import secrets
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.auth.security import hash_password, verify_password
from app.cache import check_rate_limit
from app.middleware import _client_ip
from app.dependencies import get_current_user
from app.models.conversation import Conversation, Message
from app.models.conversation_share import ConversationShare
from app.models.user import User
from app.schemas.shares import (
    ConversationShareCreate,
    ConversationShareManageOut,
    ConversationShareOut,
    SharedConversationAccessRequest,
    SharedConversationOut,
    SharedMessageOut,
)

router = APIRouter(tags=["Conversation Sharing"])

MAX_SHARED_MESSAGES = 100
MAX_SHARED_MESSAGE_CHARS = 20_000
MAX_SHARED_TOTAL_CHARS = 100_000
MAX_SHARED_SOURCES_PER_MESSAGE = 10
MAX_SHARED_SOURCE_SNIPPET_CHARS = 500


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
        password_hash=hash_password(payload.password) if payload.password else None,
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
        access_count=share.access_count,
        last_accessed_at=share.last_accessed_at,
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
            password_protected=share.password_hash is not None,
            access_count=share.access_count,
            last_accessed_at=share.last_accessed_at,
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


def _get_valid_share(token: str, db: Session) -> ConversationShare:
    if not token or len(token) > 256:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="رابط المشاركة غير صالح",
        )

    share = (
        db.query(ConversationShare)
        .join(Conversation, Conversation.id == ConversationShare.conversation_id)
        .filter(
            ConversationShare.token_hash == _hash_token(token),
            Conversation.deleted_at.is_(None),
        )
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

    return share


def _safe_shared_sources(sources: list[dict] | None) -> list[dict]:
    """Project source metadata onto the small public schema used by ChatMessage."""
    safe_sources = []
    for source in (sources or [])[:MAX_SHARED_SOURCES_PER_MESSAGE]:
        if not isinstance(source, dict):
            continue

        item = {}
        source_id = source.get("id")
        if isinstance(source_id, str) and source_id.strip():
            item["id"] = source_id.strip()[:32]

        for key, limit in (("filename", 255), ("title", 255), ("snippet", MAX_SHARED_SOURCE_SNIPPET_CHARS)):
            value = source.get(key)
            if isinstance(value, str) and value:
                item[key] = value[:limit]

        url = source.get("url")
        if isinstance(url, str) and len(url) <= 2048:
            parsed = urlsplit(url)
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                item["url"] = url

        chunk = source.get("chunk")
        if isinstance(chunk, int) and not isinstance(chunk, bool) and chunk >= 0:
            item["chunk"] = chunk

        file_id = source.get("file_id")
        if isinstance(file_id, int) and not isinstance(file_id, bool) and file_id > 0:
            item["file_id"] = file_id

        if item:
            safe_sources.append(item)
    return safe_sources


def _serialize_shared_conversation(
    share: ConversationShare, db: Session
) -> SharedConversationOut:
    conversation = share.conversation
    message_count = (
        db.query(func.count(Message.id))
        .filter(Message.conversation_id == conversation.id)
        .scalar()
        or 0
    )
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(MAX_SHARED_MESSAGES)
        .all()
    )
    messages.reverse()

    truncated = message_count > MAX_SHARED_MESSAGES
    total_chars = 0
    output_messages = []
    for message in messages:
        remaining = MAX_SHARED_TOTAL_CHARS - total_chars
        if remaining <= 0:
            truncated = True
            break

        content = message.content[: min(MAX_SHARED_MESSAGE_CHARS, remaining)]
        if len(content) < len(message.content):
            truncated = True
        total_chars += len(content)
        output_messages.append(
            SharedMessageOut(
                role=message.role.value,
                content=content,
                created_at=message.created_at,
                sources=_safe_shared_sources(message.sources),
            )
        )

    if len(output_messages) < len(messages):
        truncated = True

    return SharedConversationOut(
        title=conversation.title,
        created_at=conversation.created_at,
        expires_at=share.expires_at,
        messages=output_messages,
        truncated=truncated,
    )


def _record_share_access(share_id: int, db: Session) -> None:
    now = datetime.now(timezone.utc)
    db.execute(
        update(ConversationShare)
        .where(ConversationShare.id == share_id)
        .values(
            access_count=ConversationShare.access_count + 1,
            last_accessed_at=now,
        )
    )
    db.commit()


@router.get(
    "/shared-conversations/{token}",
    response_model=SharedConversationOut,
)
def get_shared_conversation(
    token: str,
    db: Session = Depends(get_db),
):
    share = _get_valid_share(token, db)
    if share.password_hash is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="share_password_required",
        )

    _record_share_access(share.id, db)
    share = _get_valid_share(token, db)
    return _serialize_shared_conversation(share, db)


@router.post(
    "/shared-conversations/{token}/access",
    response_model=SharedConversationOut,
)
def access_password_protected_share(
    token: str,
    payload: SharedConversationAccessRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    share = _get_valid_share(token, db)
    if share.password_hash is None:
        _record_share_access(share.id, db)
        share = _get_valid_share(token, db)
        return _serialize_shared_conversation(share, db)

    ip = _client_ip(request)
    rate_limit = check_rate_limit(
        f"share-password:{_hash_token(token)}:{ip}",
        5,
        60,
    )
    if rate_limit is None:
        if settings.ENVIRONMENT == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="خدمة تحديد المعدل غير متاحة مؤقتًا",
                headers={"Retry-After": "30"},
            )
    elif not rate_limit[0]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="محاولات كثيرة. حاول بعد دقيقة.",
            headers={"Retry-After": "60"},
        )

    if not verify_password(payload.password, share.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_share_password",
        )

    _record_share_access(share.id, db)
    share = _get_valid_share(token, db)
    return _serialize_shared_conversation(share, db)
