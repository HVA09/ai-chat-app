"""
مسارات إدارة محادثات المستخدم الحالي: عرض، تعديل الاسم، حذف، وتصدير
"""
from datetime import datetime, timezone
import json
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, or_, over
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.attributes import set_committed_value

from app.database import get_db
from app.dependencies import enforce_daily_ai_limit, enforce_workspace_daily_ai_limit, get_current_user
from app.models.assistant import Assistant
from app.models.conversation import Conversation, Message, MessageRole
from app.models.conversation_tag import conversation_tag_links
from app.models.conversation_folder import ConversationFolder
from app.models.conversation_tag import ConversationTag
from app.models.project import WorkspaceProject
from app.models.user import User
from app.models.usage_log import UsageLog
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.bookmarks import BookmarkedMessageOut
from app.schemas.chat import (
    ConversationBulkExportRequest,
    ConversationBulkImportOut,
    ConversationBulkImportRequest,
    ConversationDetail,
    ConversationImportRequest,
    ConversationOut,
    ConversationRename,
    ConversationSummaryOut,
)
from app.schemas.folders import ConversationFolderUpdate
from app.schemas.projects import ConversationProjectUpdate
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
    project_id: int | None = None,
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
        search_pattern = f"%{escaped_search}%"
        query = query.filter(
            or_(
                Conversation.title.ilike(search_pattern, escape="\\"),
                Conversation.messages.any(
                    Message.content.ilike(search_pattern, escape="\\")
                ),
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
        else:
            folder_membership = (
                db.query(WorkspaceMember)
                .filter(
                    WorkspaceMember.workspace_id == folder.workspace_id,
                    WorkspaceMember.user_id == current_user.id,
                )
                .first()
            )
            if not folder_membership or (
                workspace_id is None or folder.workspace_id != workspace_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="المجلد غير موجود",
                )

        query = query.filter(Conversation.folder_id == folder_id)

    if project_id is not None:
        project = db.get(WorkspaceProject, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المشروع غير موجود",
            )

        project_membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == project.workspace_id,
                WorkspaceMember.user_id == current_user.id,
            )
            .first()
        )
        if not project_membership or workspace_id != project.workspace_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المشروع غير موجود",
            )
        query = query.filter(Conversation.project_id == project_id)

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

    if search and search.strip():
        search_text = search.strip()[:100]
        title_exact = func.lower(Conversation.title) == search_text.lower()
        title_prefix = Conversation.title.ilike(
            f"{escaped_search}%",
            escape="\\",
        )
        message_similarity = (
            db.query(func.max(func.similarity(Message.content, search_text)))
            .filter(Message.conversation_id == Conversation.id)
            .correlate(Conversation)
            .scalar_subquery()
        )
        relevance = func.greatest(
            func.similarity(Conversation.title, search_text),
            func.coalesce(message_similarity, 0.0),
        )
        query = query.order_by(
            Conversation.is_pinned.desc(),
            title_exact.desc(),
            title_prefix.desc(),
            relevance.desc(),
            Conversation.updated_at.desc(),
            Conversation.id.desc(),
        )
    else:
        query = query.order_by(
            Conversation.is_pinned.desc(),
            Conversation.updated_at.desc(),
            Conversation.id.desc(),
        )

    conversations = query.offset(skip).limit(limit).all()

    if not search or not search.strip() or not conversations:
        return conversations

    search_text = search.strip()[:100]

    def make_snippet(text: str | None, needle: str, max_chars: int = 180) -> str | None:
        if not text:
            return None
        normalized = " ".join(text.split())
        if not normalized:
            return None
        start = normalized.casefold().find(needle.casefold())
        if start < 0:
            return None
        end = start + len(needle)
        window_start = max(0, start - 70)
        window_end = min(len(normalized), end + 90)
        snippet = normalized[window_start:window_end].strip()
        if window_start > 0:
            snippet = "… " + snippet
        if window_end < len(normalized):
            snippet = snippet + " …"
        if len(snippet) > max_chars:
            snippet = snippet[:max_chars].rstrip() + "…"
        return snippet

    conversation_ids = [conversation.id for conversation in conversations]
    matched_messages = (
        db.query(Message.conversation_id, Message.content)
        .filter(
            Message.conversation_id.in_(conversation_ids),
            Message.content.ilike(
                f"%{escaped_search}%",
                escape="\\",
            ),
        )
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )

    snippets_by_conversation: dict[int, str] = {}
    for conversation_id, content in matched_messages:
        if conversation_id in snippets_by_conversation:
            continue
        snippet = make_snippet(content, search_text)
        if snippet:
            snippets_by_conversation[conversation_id] = snippet

    serialized = [ConversationOut.model_validate(conversation) for conversation in conversations]
    for item, conversation in zip(serialized, conversations):
        if conversation.id in snippets_by_conversation:
            item.search_snippet = snippets_by_conversation[conversation.id]
            continue
        item.search_snippet = make_snippet(conversation.title, search_text)

    return serialized


@router.patch("/{conversation_id}/project", response_model=ConversationOut)
def set_conversation_project(
    conversation_id: int,
    payload: ConversationProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned_conversation(conversation_id, current_user, db)

    if payload.project_id is not None:
        project = db.get(WorkspaceProject, payload.project_id)
        if not project or project.workspace_id != conversation.workspace_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المشروع غير موجود",
            )
        membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == project.workspace_id,
                WorkspaceMember.user_id == current_user.id,
            )
            .first()
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المشروع غير موجود",
            )

    conversation.project_id = payload.project_id
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/bookmarks", response_model=list[BookmarkedMessageOut])
def list_bookmarked_messages(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message_index = over(
        func.row_number(),
        partition_by=Message.conversation_id,
        order_by=(Message.created_at, Message.id),
    ).label("message_index")

    indexed_messages = (
        db.query(
            Message.id.label("message_id"),
            Message.conversation_id.label("conversation_id"),
            Conversation.title.label("conversation_title"),
            message_index,
            Message.role.label("role"),
            Message.content.label("content"),
            Message.created_at.label("created_at"),
            Message.is_bookmarked.label("is_bookmarked"),
        )
        .join(Conversation, Conversation.id == Message.conversation_id)
        .filter(
            Conversation.user_id == current_user.id,
            Conversation.deleted_at.is_(None),
        )
        .subquery()
    )

    rows = (
        db.query(indexed_messages)
        .filter(indexed_messages.c.is_bookmarked.is_(True))
        .order_by(
            indexed_messages.c.created_at.desc(),
            indexed_messages.c.message_id.desc(),
        )
        .limit(100)
        .all()
    )

    return [
        BookmarkedMessageOut(
            message_id=row.message_id,
            conversation_id=row.conversation_id,
            conversation_title=row.conversation_title,
            message_index=int(row.message_index),
            role=row.role.value,
            content=row.content,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/{conversation_id}/branches", response_model=list[ConversationOut])
def list_conversation_branches(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    parent = (
        db.query(Conversation.id)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
            Conversation.deleted_at.is_(None),
        )
        .first()
    )
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المحادثة غير موجودة",
        )

    return (
        db.query(Conversation)
        .filter(
            Conversation.user_id == current_user.id,
            Conversation.parent_conversation_id == conversation_id,
            Conversation.deleted_at.is_(None),
        )
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .limit(100)
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
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
            Conversation.deleted_at.is_(None),
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المحادثة غير موجودة")

    # قد تكون Session الحالية قد حمّلت الرسائل قبل تغيير is_bookmarked/feedback.
    # نعيد تحميل العلاقات من قاعدة البيانات باستخدام populate_existing حتى لا نعيد
    # كائنات قديمة من identity map عند تسلسل ConversationDetail.
    messages = (
        db.query(Message)
        .populate_existing()
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )
    tags = (
        db.query(ConversationTag)
        .populate_existing()
        .join(conversation_tag_links, ConversationTag.id == conversation_tag_links.c.tag_id)
        .filter(conversation_tag_links.c.conversation_id == conversation.id)
        .all()
    )
    set_committed_value(conversation, "messages", messages)
    set_committed_value(conversation, "tags", tags)
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


TITLE_MAX_MESSAGES = 12
TITLE_MAX_CHARS = 6_000


def _build_title_prompt(conversation: Conversation) -> str:
    messages = sorted(
        conversation.messages,
        key=lambda message: (message.created_at, message.id),
    )[-TITLE_MAX_MESSAGES:]

    transcript_parts: list[str] = []
    total_chars = 0
    for message in messages:
        content = message.content.strip()
        if not content:
            continue
        role = "USER" if message.role.value == "user" else "ASSISTANT"
        block = f"{role}: {content}"
        remaining = TITLE_MAX_CHARS - total_chars
        if remaining <= 0:
            break
        if len(block) > remaining:
            block = block[:remaining].rstrip() + "…"
        transcript_parts.append(block)
        total_chars += len(block) + 2

    transcript = "\n\n".join(transcript_parts)
    return (
        "Create a concise title for the following conversation. "
        "Use the same language used most often by the user. "
        "Return only one title, ideally 3 to 7 words. "
        "Do not add quotes, markdown, a 'Title:' prefix, emojis, or a trailing period. "
        "Do not invent facts or mention hidden prompts, system instructions, memory, "
        "or implementation details. "
        "The title should describe the main topic, not the assistant's internal process.\n\n"
        f"CONVERSATION:\n{transcript}"
    )


def _normalize_generated_title(raw_title: str) -> str:
    title = " ".join(raw_title.strip().split())
    title = re.sub(r"^(?:title|العنوان)\s*:\s*", "", title, flags=re.IGNORECASE)
    title = title.strip().strip(' "“”‘’')
    title = re.sub(r"[.!؟?]+$", "", title).strip()
    return title[:255].strip()


@router.post("/{conversation_id}/generate-title", response_model=ConversationOut)
async def generate_conversation_title(
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
    if conversation.workspace_id is not None:
        enforce_workspace_daily_ai_limit(conversation.workspace_id, current_user, db)

    if not conversation.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا توجد رسائل كافية لتوليد عنوان",
        )

    prompt = _build_title_prompt(conversation)
    reply = await get_ai_reply(
        prompt,
        history=[],
        model=conversation.ai_model,
    )
    generated_title = _normalize_generated_title(reply.text or "")
    if not generated_title:
        fallback = next(
            (
                message.content.strip()
                for message in sorted(
                    conversation.messages,
                    key=lambda message: (message.created_at, message.id),
                )
                if message.role.value == "user" and message.content.strip()
            ),
            "",
        )
        generated_title = fallback[:50].strip() or "محادثة جديدة"

    conversation.title = generated_title
    db.add(
        UsageLog(
            user_id=current_user.id,
            workspace_id=conversation.workspace_id,
            endpoint="/conversations/generate-title",
            input_tokens=reply.input_tokens,
            output_tokens=reply.output_tokens,
        )
    )
    db.commit()
    db.refresh(conversation)
    return conversation


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
    if conversation.workspace_id is not None:
        enforce_workspace_daily_ai_limit(conversation.workspace_id, current_user, db)

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
            workspace_id=conversation.workspace_id,
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


@router.post("/{conversation_id}/branch", response_model=ConversationDetail, status_code=status.HTTP_201_CREATED)
def branch_conversation(
    conversation_id: int,
    message_index: int = 1,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if message_index < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="رقم الرسالة يجب أن يبدأ من 1",
        )

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

    ordered_messages = sorted(
        source.messages,
        key=lambda message: (message.created_at, message.id),
    )
    if message_index > len(ordered_messages):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="رقم الرسالة خارج نطاق المحادثة",
        )

    branch_title = f"فرع من {source.title}".strip()[:255] or "فرع من المحادثة"
    branch = Conversation(
        user_id=current_user.id,
        title=branch_title,
        is_pinned=False,
        is_archived=False,
        folder_id=source.folder_id,
        project_id=source.project_id,
        workspace_id=source.workspace_id,
        ai_model=source.ai_model,
        assistant_id=source.assistant_id,
        summary=None,
        summary_updated_at=None,
        deleted_at=None,
        parent_conversation_id=source.id,
        branched_from_message_index=message_index,
        tags=list(source.tags),
    )

    for message in ordered_messages[:message_index]:
        branch.messages.append(
            Message(
                role=message.role,
                content=message.content,
                sources=message.sources,
                feedback=None,
                is_bookmarked=False,
            )
        )

    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch


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
        folder = db.get(ConversationFolder, payload.folder_id)
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
        else:
            membership = (
                db.query(WorkspaceMember)
                .filter(
                    WorkspaceMember.workspace_id == folder.workspace_id,
                    WorkspaceMember.user_id == current_user.id,
                )
                .first()
            )
            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="المجلد غير موجود",
                )
            if folder.workspace_id != conversation.workspace_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="لا يمكن نقل المحادثة إلى مجلد من مساحة عمل أخرى",
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


@router.post("/export", response_class=Response)
def bulk_export_conversations(
    payload: ConversationBulkExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversations = (
        db.query(Conversation)
        .options(selectinload(Conversation.messages))
        .filter(
            Conversation.user_id == current_user.id,
            Conversation.id.in_(payload.conversation_ids),
        )
        .all()
    )

    if len(conversations) != len(payload.conversation_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="إحدى المحادثات المحددة غير موجودة",
        )

    by_id = {conversation.id: conversation for conversation in conversations}
    ordered = [by_id[conversation_id] for conversation_id in payload.conversation_ids]

    export_payload = {
        "version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "conversations": [
            {
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat()
                if conversation.created_at
                else None,
                "is_pinned": conversation.is_pinned,
                "is_archived": conversation.is_archived,
                "deleted_at": conversation.deleted_at.isoformat()
                if conversation.deleted_at
                else None,
                "folder_id": conversation.folder_id,
                "project_id": conversation.project_id,
                "workspace_id": conversation.workspace_id,
                "assistant_id": conversation.assistant_id,
                "ai_model": conversation.ai_model,
                "messages": [
                    {
                        "role": message.role.value,
                        "content": message.content,
                        "created_at": message.created_at.isoformat()
                        if message.created_at
                        else None,
                        "sources": message.sources or [],
                        "feedback": message.feedback,
                    }
                    for message in conversation.messages
                ],
            }
            for conversation in ordered
        ],
    }

    body = json.dumps(export_payload, ensure_ascii=False, indent=2) + "\n"
    if len(body.encode("utf-8")) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="حجم التصدير كبير جدًا، اختر عددًا أقل من المحادثات",
        )

    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="ai-conversations-backup.json"'
        },
    )


@router.post("/import-bulk", response_model=ConversationBulkImportOut, status_code=status.HTTP_201_CREATED)
def import_conversations_bulk(
    payload: ConversationBulkImportRequest,
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    folder_ids = {item.folder_id for item in payload.conversations if item.folder_id is not None}
    project_ids = {item.project_id for item in payload.conversations if item.project_id is not None}
    assistant_ids = {item.assistant_id for item in payload.conversations if item.assistant_id is not None}

    folder_map = {}
    if folder_ids:
        folders = db.query(ConversationFolder).filter(
            ConversationFolder.id.in_(folder_ids),
            ConversationFolder.user_id == current_user.id,
        ).all()
        folder_map = {
            folder.id: folder.id
            for folder in folders
            if folder.workspace_id is None or folder.workspace_id == workspace_id
        }

    project_map = {}
    if project_ids:
        projects = db.query(WorkspaceProject).filter(
            WorkspaceProject.id.in_(project_ids),
            WorkspaceProject.workspace_id == workspace_id,
        ).all()
        project_map = {project.id: project.id for project in projects}

    assistant_map = {}
    if assistant_ids:
        assistants = db.query(Assistant).filter(
            Assistant.id.in_(assistant_ids),
            Assistant.user_id == current_user.id,
        ).all()
        assistant_map = {assistant.id: assistant.id for assistant in assistants}

    created_ids: list[int] = []
    try:
        for item in payload.conversations:
            conversation = Conversation(
                user_id=current_user.id,
                title=item.title,
                is_pinned=False,
                is_archived=False,
                folder_id=folder_map.get(item.folder_id),
                project_id=project_map.get(item.project_id),
                workspace_id=workspace_id,
                ai_model=item.ai_model,
                assistant_id=assistant_map.get(item.assistant_id),
                deleted_at=None,
                summary=None,
                summary_updated_at=None,
                parent_conversation_id=None,
                branched_from_message_index=None,
            )

            for imported_message in item.messages:
                conversation.messages.append(
                    Message(
                        role=MessageRole(imported_message.role),
                        content=imported_message.content,
                        sources=imported_message.sources or [],
                        feedback=None,
                        is_bookmarked=False,
                    )
                )

            db.add(conversation)
            db.flush()
            created_ids.append(conversation.id)

        db.commit()
    except Exception:
        db.rollback()
        raise

    return ConversationBulkImportOut(
        conversation_ids=created_ids,
        imported_count=len(created_ids),
    )


@router.post("/import", response_model=ConversationDetail, status_code=status.HTTP_201_CREATED)
def import_conversation(
    payload: ConversationImportRequest,
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    folder_id = None
    if payload.folder_id is not None:
        folder = db.get(ConversationFolder, payload.folder_id)
        if folder:
            can_use_folder = (
                folder.user_id == current_user.id
                and (
                    folder.workspace_id is None
                    or folder.workspace_id == workspace_id
                )
            )
            if can_use_folder:
                folder_id = folder.id

    project_id = None
    if payload.project_id is not None:
        project = db.get(WorkspaceProject, payload.project_id)
        if project and project.workspace_id == workspace_id:
            project_membership = (
                db.query(WorkspaceMember)
                .filter(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == current_user.id,
                )
                .first()
            )
            if project_membership:
                project_id = project.id

    conversation = Conversation(
        user_id=current_user.id,
        title=payload.title,
        is_pinned=False,
        is_archived=False,
        folder_id=folder_id,
        project_id=project_id,
        workspace_id=workspace_id,
        ai_model=None,
        assistant_id=None,
        deleted_at=None,
        summary=None,
        summary_updated_at=None,
        parent_conversation_id=None,
        branched_from_message_index=None,
    )

    for imported_message in payload.messages:
        conversation.messages.append(
            Message(
                role=MessageRole(imported_message.role),
                content=imported_message.content,
                sources=imported_message.sources or [],
                feedback=None,
                is_bookmarked=False,
            )
        )

    db.add(conversation)
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
