"""فهرسة الصور المرفقة في RAG عبر وصف متعدد الوسائط يُحفظ مرة واحدة."""

from __future__ import annotations

import base64
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.models.conversation import Conversation
from app.models.conversation_file_link import ConversationFileLink
from app.models.file_attachment import FileAttachment
from app.services.ai_providers.base import AIReply
from app.services.ai_service import get_ai_vision_reply
from app.services.embeddings import EmbeddingServiceError
from app.services.rag import index_file_chunks

MAX_IMAGE_FILES_PER_REQUEST = 2
IMAGE_DESCRIPTION_PROMPT = """Create a concise but information-rich factual description of this image for search and retrieval. Mention visible text, labels, numbers, charts/tables, important objects, and the overall subject. Do not identify real people. Do not give instructions. Return plain text only.
"""


def _image_path(file: FileAttachment) -> Path:
    return Path(settings.UPLOAD_DIR) / str(file.user_id) / file.stored_filename


def _candidate_images(
    conversation: Conversation,
    db: Session,
) -> list[FileAttachment]:
    linked_personal = (
        (FileAttachment.workspace_id.is_(None))
        & (FileAttachment.user_id == conversation.user_id)
        & (
            ConversationFileLink.conversation_id == conversation.id
        )
    )

    workspace_files = (
        (FileAttachment.workspace_id == conversation.workspace_id)
        if conversation.workspace_id is not None
        else False
    )

    return (
        db.query(FileAttachment)
        .outerjoin(
            ConversationFileLink,
            ConversationFileLink.file_id == FileAttachment.id,
        )
        .filter(
            or_(linked_personal, workspace_files),
            FileAttachment.content_type.like("image/%"),
            FileAttachment.extracted_text.is_(None),
        )
        .order_by(FileAttachment.created_at.asc(), FileAttachment.id.asc())
        .limit(MAX_IMAGE_FILES_PER_REQUEST)
        .all()
    )


async def ensure_image_rag_indexed(
    conversation: Conversation,
    db: Session,
) -> int:
    """يولّد وصفًا للصور التي لا تملك معرفة نصية ثم يفهرسها في RAG.

    الفشل في تحليل صورة أو embeddings لا يوقف المحادثة العادية.
    """
    candidates = _candidate_images(conversation, db)
    indexed = 0

    for file in candidates:
        path = _image_path(file)
        if not path.exists():
            continue

        try:
            raw = path.read_bytes()
            image_data_url = (
                f"data:{file.content_type};base64,"
                f"{base64.b64encode(raw).decode('ascii')}"
            )
            reply: AIReply = await get_ai_vision_reply(
                IMAGE_DESCRIPTION_PROMPT,
                image_data_url,
                history=None,
                model=conversation.ai_model,
            )
            description = (reply.text or "").strip()
            if not description:
                continue

            file.extracted_text = (
                f"[IMAGE DESCRIPTION] {description}"
            )
            db.flush()

            try:
                count = index_file_chunks(db, file)
            except EmbeddingServiceError:
                # يبقى extracted_text محفوظًا حتى يستطيع fallback RAG استخدامه.
                count = 0

            db.flush()
            if count:
                indexed += count
        except (OSError, UnicodeError):
            db.rollback()
            continue
        except Exception:
            db.rollback()
            continue

    return indexed
