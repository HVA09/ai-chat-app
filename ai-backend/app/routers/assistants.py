"""إدارة المساعدين المخصصين للمستخدم الحالي."""
import difflib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.assistant import Assistant
from app.models.conversation import Conversation, Message
from app.models.assistant_file_link import AssistantFileLink
from app.models.file_attachment import FileAttachment
from app.models.assistant_version import AssistantVersion
from app.models.user import User
from app.schemas.assistant_versions import AssistantVersionCompareOut, AssistantVersionOut
from app.schemas.assistants import (
    AssistantAnalyticsOut,
    AssistantAnalyticsPointOut,
    AssistantCreate,
    AssistantOut,
    AssistantUpdate,
)
from app.schemas.file import FileOut

router = APIRouter(prefix="/assistants", tags=["Assistants"])

def _create_assistant_version(assistant: Assistant, db: Session) -> AssistantVersion:
    current_version = db.query(func.max(AssistantVersion.version)).filter(
        AssistantVersion.assistant_id == assistant.id
    ).scalar() or 0
    version = AssistantVersion(
        assistant_id=assistant.id,
        version=current_version + 1,
        name=assistant.name,
        description=assistant.description,
        instructions=assistant.instructions,
    )
    db.add(version)
    return version



def _get_owned_assistant(
    assistant_id: int, current_user: User, db: Session
) -> Assistant:
    assistant = (
        db.query(Assistant)
        .filter(
            Assistant.id == assistant_id,
            Assistant.user_id == current_user.id,
        )
        .first()
    )
    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المساعد غير موجود",
        )
    return assistant


def _ensure_unique_name(
    name: str,
    current_user: User,
    db: Session,
    exclude_id: int | None = None,
) -> None:
    query = db.query(Assistant).filter(
        Assistant.user_id == current_user.id,
        func.lower(Assistant.name) == name.lower(),
    )
    if exclude_id is not None:
        query = query.filter(Assistant.id != exclude_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="يوجد مساعد بهذا الاسم",
        )


@router.get("", response_model=list[AssistantOut])
def list_assistants(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Assistant)
        .filter(Assistant.user_id == current_user.id)
        .order_by(Assistant.created_at.asc(), Assistant.id.asc())
        .all()
    )


@router.post("", response_model=AssistantOut, status_code=status.HTTP_201_CREATED)
def create_assistant(
    payload: AssistantCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_unique_name(payload.name, current_user, db)
    assistant = Assistant(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        instructions=payload.instructions,
    )
    db.add(assistant)
    db.flush()
    _create_assistant_version(assistant, db)
    db.commit()
    db.refresh(assistant)
    return assistant


@router.patch("/{assistant_id}", response_model=AssistantOut)
def update_assistant(
    assistant_id: int,
    payload: AssistantUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assistant = _get_owned_assistant(assistant_id, current_user, db)

    if payload.name is not None:
        _ensure_unique_name(payload.name, current_user, db, exclude_id=assistant.id)
        assistant.name = payload.name
    if payload.description is not None:
        assistant.description = payload.description
    if payload.instructions is not None:
        assistant.instructions = payload.instructions

    db.flush()
    _create_assistant_version(assistant, db)
    db.commit()
    db.refresh(assistant)
    return assistant


@router.get("/{assistant_id}/analytics", response_model=AssistantAnalyticsOut)
def get_assistant_analytics(
    assistant_id: int,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assistant = _get_owned_assistant(assistant_id, current_user, db)
    days = min(max(days, 1), 90)
    since = func.now() - func.make_interval(0, 0, 0, days)

    conversation_count = (
        db.query(func.count(Conversation.id))
        .filter(
            Conversation.assistant_id == assistant.id,
            Conversation.updated_at >= since,
            Conversation.deleted_at.is_(None),
        )
        .scalar()
        or 0
    )
    message_count = (
        db.query(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(
            Conversation.assistant_id == assistant.id,
            Message.created_at >= since,
            Conversation.deleted_at.is_(None),
        )
        .scalar()
        or 0
    )
    active_user_count = (
        db.query(func.count(func.distinct(Conversation.user_id)))
        .filter(
            Conversation.assistant_id == assistant.id,
            Conversation.updated_at >= since,
            Conversation.deleted_at.is_(None),
        )
        .scalar()
        or 0
    )
    last_used_at = (
        db.query(func.max(Conversation.updated_at))
        .filter(
            Conversation.assistant_id == assistant.id,
            Conversation.deleted_at.is_(None),
        )
        .scalar()
    )
    return AssistantAnalyticsOut(
        assistant_id=assistant.id,
        days=days,
        conversation_count=conversation_count,
        message_count=message_count,
        active_user_count=active_user_count,
        last_used_at=last_used_at,
    )


@router.get("/{assistant_id}/analytics/daily", response_model=list[AssistantAnalyticsPointOut])
def get_assistant_analytics_daily(
    assistant_id: int,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assistant = _get_owned_assistant(assistant_id, current_user, db)
    days = min(max(days, 7), 90)
    since = datetime.now(timezone.utc) - timedelta(days=days - 1)

    day_expr = func.date_trunc("day", Conversation.created_at)
    conversation_rows = (
        db.query(day_expr, func.count(Conversation.id))
        .filter(
            Conversation.assistant_id == assistant.id,
            Conversation.created_at >= since,
            Conversation.deleted_at.is_(None),
        )
        .group_by(day_expr)
        .all()
    )

    message_day_expr = func.date_trunc("day", Message.created_at)
    message_rows = (
        db.query(message_day_expr, func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(
            Conversation.assistant_id == assistant.id,
            Message.created_at >= since,
            Conversation.deleted_at.is_(None),
        )
        .group_by(message_day_expr)
        .all()
    )

    active_day_expr = func.date_trunc("day", Conversation.updated_at)
    active_user_rows = (
        db.query(active_day_expr, func.count(func.distinct(Conversation.user_id)))
        .filter(
            Conversation.assistant_id == assistant.id,
            Conversation.updated_at >= since,
            Conversation.deleted_at.is_(None),
        )
        .group_by(active_day_expr)
        .all()
    )

    conversations_by_day = {row[0].date(): int(row[1]) for row in conversation_rows}
    messages_by_day = {row[0].date(): int(row[1]) for row in message_rows}
    users_by_day = {row[0].date(): int(row[1]) for row in active_user_rows}

    today = datetime.now(timezone.utc).date()
    points = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        points.append(
            AssistantAnalyticsPointOut(
                date=day.isoformat(),
                conversations=conversations_by_day.get(day, 0),
                messages=messages_by_day.get(day, 0),
                active_users=users_by_day.get(day, 0),
            )
        )
    return points


@router.get("/{assistant_id}/versions", response_model=list[AssistantVersionOut])
def list_assistant_versions(
    assistant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assistant = _get_owned_assistant(assistant_id, current_user, db)
    return (
        db.query(AssistantVersion)
        .filter(AssistantVersion.assistant_id == assistant.id)
        .order_by(AssistantVersion.version.desc())
        .all()
    )


@router.get("/{assistant_id}/versions/{version}/compare-current", response_model=AssistantVersionCompareOut)
def compare_assistant_version_with_current(
    assistant_id: int,
    version: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assistant = _get_owned_assistant(assistant_id, current_user, db)
    snapshot = (
        db.query(AssistantVersion)
        .filter(
            AssistantVersion.assistant_id == assistant.id,
            AssistantVersion.version == version,
        )
        .first()
    )
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="نسخة المساعد غير موجودة",
        )

    previous = [
        f"name: {snapshot.name}",
        f"description: {snapshot.description or ''}",
        "instructions:",
        snapshot.instructions,
    ]
    current = [
        f"name: {assistant.name}",
        f"description: {assistant.description or ''}",
        "instructions:",
        assistant.instructions,
    ]
    diff = "\n".join(
        difflib.unified_diff(
            previous,
            current,
            fromfile=f"version-{snapshot.version}",
            tofile="current",
            lineterm="",
        )
    )
    return AssistantVersionCompareOut(
        from_version=snapshot.version,
        current_version=(
            db.query(func.max(AssistantVersion.version))
            .filter(AssistantVersion.assistant_id == assistant.id)
            .scalar()
            or 0
        ),
        diff=diff[:20000],
        changed=previous != current,
    )


@router.post("/{assistant_id}/versions/{version}/restore", response_model=AssistantOut)
def restore_assistant_version(
    assistant_id: int,
    version: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assistant = _get_owned_assistant(assistant_id, current_user, db)
    snapshot = (
        db.query(AssistantVersion)
        .filter(
            AssistantVersion.assistant_id == assistant.id,
            AssistantVersion.version == version,
        )
        .first()
    )
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="نسخة المساعد غير موجودة",
        )

    if snapshot.name != assistant.name:
        _ensure_unique_name(snapshot.name, current_user, db, exclude_id=assistant.id)
    assistant.name = snapshot.name
    assistant.description = snapshot.description
    assistant.instructions = snapshot.instructions
    db.flush()
    _create_assistant_version(assistant, db)
    db.commit()
    db.refresh(assistant)
    return assistant


@router.delete("/{assistant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assistant(
    assistant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assistant = _get_owned_assistant(assistant_id, current_user, db)
    db.delete(assistant)
    db.commit()


MAX_KNOWLEDGE_FILES = 20


def _get_owned_personal_file(file_id: int, current_user: User, db: Session) -> FileAttachment:
    file = (
        db.query(FileAttachment)
        .filter(
            FileAttachment.id == file_id,
            FileAttachment.user_id == current_user.id,
            FileAttachment.workspace_id.is_(None),
            FileAttachment.project_id.is_(None),
        )
        .first()
    )
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملف غير موجود")
    return file


@router.get("/{assistant_id}/files", response_model=list[FileOut])
def list_assistant_files(
    assistant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assistant = _get_owned_assistant(assistant_id, current_user, db)
    files = (
        db.query(FileAttachment)
        .join(AssistantFileLink, AssistantFileLink.file_id == FileAttachment.id)
        .filter(AssistantFileLink.assistant_id == assistant.id)
        .order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc())
        .all()
    )
    result = [FileOut.model_validate(file) for file in files]
    for item in result:
        item.is_attached = True
        item.is_owner = True
        item.can_delete = True
        item.is_ai_indexed = False
    for item, file in zip(result, files):
        item.workspace_id = file.workspace_id
        item.project_id = file.project_id
        item.is_ai_indexed = file.extracted_text is not None
    return result


@router.post("/{assistant_id}/files/{file_id}", response_model=FileOut)
def attach_assistant_file(
    assistant_id: int,
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assistant = _get_owned_assistant(assistant_id, current_user, db)
    file = _get_owned_personal_file(file_id, current_user, db)
    current_count = (
        db.query(AssistantFileLink)
        .filter(AssistantFileLink.assistant_id == assistant.id)
        .count()
    )
    if current_count >= MAX_KNOWLEDGE_FILES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="وصلت للحد الأقصى لملفات معرفة المساعد")
    link = (
        db.query(AssistantFileLink)
        .filter(
            AssistantFileLink.assistant_id == assistant.id,
            AssistantFileLink.file_id == file.id,
        )
        .first()
    )
    if not link:
        db.add(AssistantFileLink(assistant_id=assistant.id, file_id=file.id))
        db.commit()
    result = FileOut.model_validate(file)
    result.is_attached = True
    result.is_owner = True
    result.can_delete = True
    result.is_ai_indexed = file.extracted_text is not None
    return result


@router.delete("/{assistant_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def detach_assistant_file(
    assistant_id: int,
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assistant = _get_owned_assistant(assistant_id, current_user, db)
    _get_owned_personal_file(file_id, current_user, db)
    link = (
        db.query(AssistantFileLink)
        .filter(
            AssistantFileLink.assistant_id == assistant.id,
            AssistantFileLink.file_id == file_id,
        )
        .first()
    )
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ملف المعرفة غير مرتبط بهذا المساعد")
    db.delete(link)
    db.commit()
