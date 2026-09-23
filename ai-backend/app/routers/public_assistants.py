"""روابط عامة آمنة للمساعدين المخصصين ونسخها إلى حساب المستخدم الحالي."""
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.assistant import Assistant
from app.models.assistant_version import AssistantVersion
from app.models.user import User
from app.schemas.assistant_public import (
    AssistantPublicDuplicateOut,
    AssistantPublicOut,
)

router = APIRouter(prefix="/public/assistants", tags=["Public Assistants"])


def _find_public_assistant(token: str, db: Session) -> Assistant:
    normalized = token.strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المساعد غير موجود",
        )

    assistant = (
        db.query(Assistant)
        .filter(
            Assistant.public_token == normalized,
            Assistant.is_public.is_(True),
        )
        .first()
    )
    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المساعد غير موجود أو تم إلغاء الرابط",
        )
    return assistant


def _unique_copy_name(assistant: Assistant, current_user: User, db: Session) -> str:
    base = f"{assistant.name} (Copy)"
    candidate = base[:100]
    index = 2
    while (
        db.query(Assistant.id)
        .filter(
            Assistant.user_id == current_user.id,
            func.lower(Assistant.name) == candidate.lower(),
        )
        .first()
    ):
        suffix = f" (Copy {index})"
        candidate = f"{assistant.name[:100 - len(suffix)]}{suffix}"
        index += 1
    return candidate


@router.get("/{token}", response_model=AssistantPublicOut)
def get_public_assistant(
    token: str,
    db: Session = Depends(get_db),
):
    assistant = _find_public_assistant(token, db)
    # لا نرجّع instructions أو ملفات المعرفة أو أي بيانات خاصة.
    return assistant


@router.post(
    "/{token}/duplicate",
    response_model=AssistantPublicDuplicateOut,
    status_code=status.HTTP_201_CREATED,
)
def duplicate_public_assistant(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assistant = _find_public_assistant(token, db)

    clone = Assistant(
        user_id=current_user.id,
        name=_unique_copy_name(assistant, current_user, db),
        description=assistant.description,
        instructions=assistant.instructions,
        is_public=False,
        public_token=None,
    )
    db.add(clone)
    db.flush()

    version = AssistantVersion(
        assistant_id=clone.id,
        version=1,
        name=clone.name,
        description=clone.description,
        instructions=clone.instructions,
    )
    db.add(version)
    db.commit()
    db.refresh(clone)

    return AssistantPublicDuplicateOut(
        conversation_assistant_id=clone.id,
        name=clone.name,
    )
