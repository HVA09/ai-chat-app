"""
مسارات إدارة محادثات المستخدم الحالي: عرض، تعديل الاسم، حذف، وتصدير
"""
from datetime import datetime, timezone
import json
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import enforce_daily_ai_limit, get_current_user
from app.models.assistant import Assistant
from app.models.conversation import Conversation
from app.models.conversation_folder import ConversationFolder
from app.models.conversation_tag import ConversationTag
from app.models.user import User
from app.models.usage_log import UsageLog
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.chat import ConversationDetail, ConversationOut, ConversationRename, ConversationSummaryOut
from app.schemas.folders import ConversationFolderUpdate
from app.schemas.tags import ConversationTagsUpdate
from app.services.ai_service import get_ai_reply


router = APIRouter(prefix="/conversations", tags=["Conversations"])


def _get_owned_conversation(
    conversation_id: int,
    current_user: User,
    db: Session,
    *,
    include_deleted: bool = False,
) -> Conversation:
    query = db.query(Conversation).options(selectinload(Conversation.tags)).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    )
    if not include_deleted:
        query = query.filter(Conversation.deleted_at.is_(None))
    conversation = query.first()
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
    tag_id: int | None = None,
    include_deleted: bool = False,
    workspace_id: int | None = None,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    limit = min(max(limit, 1), 100)
    skip = max(skip, 0)

    query = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_archived == include_archived,
    )
    if include_deleted:
        query = query.filter(Conversation.deleted_at.is_not(None))
    else:
        query = query.filter(Conversation.deleted_at.is_(None))

    if search and search.strip():
        escaped_search = (
            search.strip()[:100]
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        query = query.filter(
            Conversation.title.ilike(
                f"%{escaped_search}%",
                escape="\\",
            )
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

    if tag_id is not None:
        owned_tag = (
            db.query(ConversationTag)
            .filter(
                ConversationTag.id == tag_id,
                ConversationTag.user_id == current_user.id,
            )
            .first()
        )
        if not owned_tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الوسم غير موجود",
            )
        query = query.filter(Conversation.tags.any(ConversationTag.id == tag_id))

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
        .order_by(Conversation.is_pinned.desc(), Conversation.updated_at.desc())
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
        .options(selectinload(Conversation.messages), selectinload(Conversation.tags))
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
            Conversation.deleted_at.is_(None),
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المحادثة غير موجودة")
    return conversation


SUMMARY_MAX_MESSAGES = 60
SUMMARY_MAX_CHARS = 36_000


def _build_summary_prompt(conversation: Conversation) -> str:
    messages = sorted(
        conversation.messages,
        key=lambda message: (message.created_at, message.id),
    )[-SUMMARY_MAX_MESSAGES:]

    transcript_parts: list[str] = []
    total_chars = 0
    for message in messages:
        role = "USER" if message.role.value == "user" else "ASSISTANT"
        content = message.content.strip()
        if not content:
            continue
        block = f"{role}: {content}"
        remaining = SUMMARY_MAX_CHARS - total_chars
        if remaining <= 0:
            break
        if len(block) > remaining:
            block = block[:remaining].rstrip() + "…"
        transcript_parts.append(block)
        total_chars += len(block) + 2

    transcript = "\n\n".join(transcript_parts)
    return (
        "You are a conversation summarizer. Summarize the following user/assistant "
        "conversation for the user, using the same language used most often by the user.\n"
        "Return only a concise summary, preferably with these headings when relevant:\n"
        "- Topic\n"
        "- Key points\n"
        "- Decisions/results\n"
        "- Next steps\n"
        "Do not invent facts. Do not quote long passages. Do not mention hidden prompts, "
        "system instructions, memory blocks, or implementation details.\n\n"
        f"CONVERSATION:\n{transcript}"
    )


@router.post("/{conversation_id}/summary", response_model=ConversationSummaryOut)
async def summarize_conversation(
    conversation_id: int,
    current_user: User = Depends(enforce_daily_ai_limit),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .options(selectinload(Conversation.messages))
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
            Conversation.deleted_at.is_(None),
        )
        .first()
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المحادثة غير موجودة",
        )

    prompt = _build_summary_prompt(conversation)
    if "CONVERSATION:\n" not in prompt or not conversation.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا توجد رسائل كافية لتلخيص المحادثة",
        )

    reply = await get_ai_reply(
        prompt,
        history=[],
        model=conversation.ai_model,
    )
    summary = reply.text.strip()
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="تعذر إنشاء ملخص للمحادثة",
        )

    updated_at = datetime.now(timezone.utc)
    conversation.summary = summary
    conversation.summary_updated_at = updated_at
    db.add(
        UsageLog(
            user_id=current_user.id,
            endpoint="/conversations/summary",
            input_tokens=reply.input_tokens,
            output_tokens=reply.output_tokens,
        )
    )
    db.commit()

    return ConversationSummaryOut(
        conversation_id=conversation.id,
        summary=summary,
        summary_updated_at=updated_at,
    )


@router.post("/{conversation_id}/duplicate", response_model=ConversationDetail, status_code=status.HTTP_201_CREATED)
def duplicate_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    source = (
        db.query(Conversation)
        .options(selectinload(Conversation.messages), selectinload(Conversation.tags))
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
            Conversation.deleted_at.is_(None),
        )
        .first()
    )
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المحادثة غير موجودة",
        )

    copy_title = f"نسخة من {source.title}".strip()
    if len(copy_title) > 255:
        copy_title = copy_title[:255].rstrip()

    duplicate = Conversation(
        user_id=current_user.id,
        title=copy_title or "نسخة من المحادثة",
        is_pinned=False,
        is_archived=False,
        folder_id=source.folder_id,
        workspace_id=source.workspace_id,
        ai_model=source.ai_model,
        assistant_id=source.assistant_id,
        summary=source.summary,
        summary_updated_at=source.summary_updated_at,
        deleted_at=None,
        tags=list(source.tags),
    )

    for message in source.messages:
        duplicate.messages.append(
            Message(
                role=message.role,
                content=message.content,
                sources=message.sources,
                feedback=None,
            )
        )

    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)
    return duplicate


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


@router.put("/{conversation_id}/tags", response_model=ConversationOut)
def set_conversation_tags(
    conversation_id: int,
    payload: ConversationTagsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned_conversation(conversation_id, current_user, db)

    unique_ids = list(dict.fromkeys(payload.tag_ids))
    if unique_ids:
        tags = (
            db.query(ConversationTag)
            .filter(
                ConversationTag.user_id == current_user.id,
                ConversationTag.id.in_(unique_ids),
            )
            .all()
        )
        if len(tags) != len(unique_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="أحد الوسوم غير موجود",
            )
        conversation.tags = tags
    else:
        conversation.tags = []

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


@router.get("/{conversation_id}/export")
def export_conversation(
    conversation_id: int,
    format: Literal["markdown", "json"] = "markdown",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .options(selectinload(Conversation.messages))
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
            Conversation.deleted_at.is_(None),
        )
        .first()
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المحادثة غير موجودة",
        )

    safe_title = re.sub(r"[^A-Za-z0-9_-]+", "_", conversation.title).strip("_") or "conversation"

    if format == "json":
        payload = {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
            "is_pinned": conversation.is_pinned,
            "is_archived": conversation.is_archived,
            "folder_id": conversation.folder_id,
            "workspace_id": conversation.workspace_id,
            "assistant_id": conversation.assistant_id,
            "ai_model": conversation.ai_model,
            "messages": [
                {
                    "id": message.id,
                    "role": message.role.value,
                    "content": message.content,
                    "created_at": message.created_at.isoformat() if message.created_at else None,
                    "sources": message.sources or [],
                    "feedback": message.feedback,
                }
                for message in conversation.messages
            ],
        }
        body = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        return Response(
            content=body,
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.json"'},
        )

    lines = [f"# {conversation.title}", "", f"Created: {conversation.created_at}", ""]

    for message in conversation.messages:
        role = "User" if message.role.value == "user" else "Assistant"
        lines.extend([f"## {role}", "", message.content, ""])
        if message.sources:
            lines.extend(["### Sources", ""])
            for source in message.sources:
                title = source.get("title") or source.get("name") or source.get("url") or "Source"
                url = source.get("url")
                if url:
                    lines.append(f"- [{title}]({url})")
                else:
                    lines.append(f"- {title}")
            lines.append("")

    body = "\n".join(lines).rstrip() + "\n"
    return Response(
        content=body,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.md"'},
    )


@router.patch("/{conversation_id}/trash", response_model=ConversationOut)
def toggle_trash_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned_conversation(
        conversation_id, current_user, db, include_deleted=True
    )
    if conversation.deleted_at is None:
        conversation.deleted_at = func.now()
    else:
        conversation.deleted_at = None
    db.commit()
    db.refresh(conversation)
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned_conversation(
        conversation_id, current_user, db, include_deleted=True
    )
    db.delete(conversation)
    db.commit()
