"""إدارة مفاتيح API الشخصية + نقطة chat بسيطة للمطورين."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import (
    enforce_daily_ai_limit,
    enforce_workspace_daily_ai_limit,
    get_current_user,
)
from app.models.api_key import APIKey
from app.models.conversation import Message
from app.models.usage_log import UsageLog
from app.models.user import User
from app.routers.chat import _augment_message, _build_history, _get_or_create_conversation
from app.schemas.api_keys import (
    APIChatRequest,
    APIChatResponse,
    APIKeyCreate,
    APIKeyCreatedOut,
    APIKeyOut,
    APIKeyUsageOut,
)
from app.services.ai_service import get_ai_reply

router = APIRouter(tags=["Developer API"])


def _hash_api_key(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _new_api_key() -> tuple[str, str, str]:
    secret = f"ak_live_{secrets.token_urlsafe(32)}"
    prefix = secret[:16]
    return secret, prefix, _hash_api_key(secret)


def _get_owned_api_key(key_id: int, current_user: User, db: Session) -> APIKey:
    key = (
        db.query(APIKey)
        .filter(APIKey.id == key_id, APIKey.user_id == current_user.id)
        .first()
    )
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مفتاح API غير موجود",
        )
    return key


@router.get("/api-keys", response_model=list[APIKeyOut])
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(APIKey)
        .filter(APIKey.user_id == current_user.id)
        .order_by(APIKey.created_at.desc(), APIKey.id.desc())
        .all()
    )


@router.post("/api-keys", response_model=APIKeyCreatedOut, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    secret, prefix, key_hash = _new_api_key()
    api_key = APIKey(
        user_id=current_user.id,
        name=payload.name,
        key_prefix=prefix,
        key_hash=key_hash,
        daily_request_limit=payload.daily_request_limit,
        expires_at=payload.expires_at,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return APIKeyCreatedOut(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        revoked_at=api_key.revoked_at,
        daily_request_limit=api_key.daily_request_limit,
        expires_at=api_key.expires_at,
        secret=secret,
    )


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    api_key = _get_owned_api_key(key_id, current_user, db)
    if api_key.revoked_at is None:
        api_key.revoked_at = datetime.now(timezone.utc)
        db.commit()


def _get_api_key_auth(
    x_api_key: str | None,
    db: Session,
) -> tuple[User, APIKey]:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key مطلوب",
        )

    key_hash = _hash_api_key(x_api_key)
    api_key = (
        db.query(APIKey)
        .filter(APIKey.key_hash == key_hash, APIKey.revoked_at.is_(None))
        .first()
    )
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="مفتاح API غير صالح أو مُلغى",
        )

    if api_key.expires_at is not None and api_key.expires_at < datetime.now(timezone.utc).date():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="انتهت صلاحية مفتاح API",
        )

    user = db.get(User, api_key.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="الحساب غير صالح",
        )

    now = datetime.now(timezone.utc)
    if api_key.last_used_at is None or now - api_key.last_used_at >= timedelta(minutes=5):
        api_key.last_used_at = now
        db.commit()

    return user, api_key


@router.get("/api-keys/{key_id}/usage", response_model=APIKeyUsageOut)
def get_api_key_usage(
    key_id: int,
    window_hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if window_hours < 1 or window_hours > 720:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="window_hours يجب أن يكون بين 1 و720",
        )

    api_key = _get_owned_api_key(key_id, current_user, db)
    since = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    used_requests, input_tokens, output_tokens = (
        db.query(
            func.count(UsageLog.id),
            func.coalesce(func.sum(UsageLog.input_tokens), 0),
            func.coalesce(func.sum(UsageLog.output_tokens), 0),
        )
        .filter(
            UsageLog.api_key_id == api_key.id,
            UsageLog.created_at >= since,
        )
        .one()
    )

    input_tokens = int(input_tokens or 0)
    output_tokens = int(output_tokens or 0)
    return APIKeyUsageOut(
        key_id=api_key.id,
        window_hours=window_hours,
        used_requests=int(used_requests or 0),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
    )


def _enforce_api_key_daily_limit(api_key: APIKey, db: Session) -> None:
    if api_key.daily_request_limit is None:
        return

    since = datetime.now(timezone.utc) - timedelta(days=1)
    used = (
        db.query(func.count(UsageLog.id))
        .filter(
            UsageLog.api_key_id == api_key.id,
            UsageLog.created_at >= since,
        )
        .scalar()
        or 0
    )
    if used >= api_key.daily_request_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"وصل مفتاح API إلى حده اليومي "
                f"({api_key.daily_request_limit} طلب)."
            ),
        )


@router.post("/v1/chat", response_model=APIChatResponse)
async def developer_chat(
    payload: APIChatRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    current_user, api_key = _get_api_key_auth(x_api_key, db)
    _enforce_api_key_daily_limit(api_key, db)
    enforce_daily_ai_limit(current_user=current_user, db=db)

    chat_payload = type(
        "APIChatPayload",
        (),
        {
            "workspace_id": payload.workspace_id,
            "assistant_id": payload.assistant_id,
            "model": payload.model,
            "conversation_id": payload.conversation_id,
            "message": payload.message,
        },
    )()
    conversation = _get_or_create_conversation(chat_payload, current_user, db)
    enforce_workspace_daily_ai_limit(conversation.workspace_id, current_user, db)

    history = _build_history(conversation, db)
    ai_message, _sources = await _augment_message(payload.message, conversation, db)
    reply = await get_ai_reply(ai_message, history, conversation.ai_model)

    db.add(
        Message(
            conversation_id=conversation.id,
            role="user",
            content=payload.message,
        )
    )
    db.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content=reply.text,
        )
    )
    db.add(
        UsageLog(
            user_id=current_user.id,
            workspace_id=conversation.workspace_id,
            endpoint="/v1/chat",
            api_key_id=api_key.id,
            input_tokens=reply.input_tokens,
            output_tokens=reply.output_tokens,
        )
    )
    db.commit()

    return APIChatResponse(
        conversation_id=conversation.id,
        reply=reply.text,
        model=conversation.ai_model,
    )
