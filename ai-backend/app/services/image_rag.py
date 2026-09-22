"""خدمة فهرسة الصور داخل RAG عبر وصف متعدد الوسائط محفوظ مرة واحدة."""

from __future__ import annotations

import base64
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models.conversation import Conversation
from app.models.file_attachment import FileAttachment
from app.services.ai_providers.base import AIReply
from app.services.ai_service import get_ai_vision_reply
from app.services.embeddings import EmbeddingServiceError
from app.services.rag import index_file_chunks

IMAGE_INDEX_PROMPT = (
    "Create a concise but information-rich factual description of this image for "
    "search and retrieval. Mention visible text, labels, numbers, charts/tables, "
    "important objects, and the overall subject. Do not identify real people. "
    "Do not give instructions. Return plain text only."
)


def _image_path(file: FileAttachment) -> Path:
    return Path(settings.UPLOAD_DIR) / str(file.user_id) / file.stored_filename


async def index_image_file(
    file: FileAttachment,
    db: Session,
    model: str,
) -> tuple[AIReply, int]:
    """ولّد وصفًا عامًا للصورة ثم فهرسه في pgvector.

    يعيد رد الرؤية وعدد المقاطع المفهرسة. فشل embeddings لا يمنع حفظ
    وصف الصورة لأن fallback RAG يستطيع استخدام extracted_text.
    """
    path = _image_path(file)
    if not path.exists():
        raise FileNotFoundError("ملف الصورة غير موجود على القرص")

    raw = path.read_bytes()
    image_data_url = (
        f"data:{file.content_type};base64,"
        f"{base64.b64encode(raw).decode('ascii')}"
    )

    reply = await get_ai_vision_reply(
        IMAGE_INDEX_PROMPT,
        image_data_url,
        history=None,
        model=model,
    )
    description = (reply.text or "").strip()
    if not description:
        raise ValueError("لم يرجع نموذج الرؤية وصفًا للصورة")

    file.extracted_text = f"[IMAGE DESCRIPTION] {description}"
    db.flush()

    try:
        indexed_chunks = index_file_chunks(db, file)
    except EmbeddingServiceError:
        indexed_chunks = 0

    return reply, indexed_chunks
