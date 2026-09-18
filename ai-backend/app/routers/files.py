"""
مسارات رفع الملفات وإدارتها: صور، PDF، Word، Excel، CSV
تُخزَّن الملفات على القرص (مجلد UPLOAD_DIR) والبيانات الوصفية بقاعدة البيانات
"""
import uuid
from pathlib import Path
import tempfile
import zipfile
from sqlalchemy import and_, case, func

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.audit import log_event
from app.models.conversation import Conversation
from app.models.conversation_file_link import ConversationFileLink
from app.models.file_attachment import FileAttachment
from app.models.user import User
from app.schemas.file import FileOut
from app.services.embeddings import EmbeddingServiceError
from app.services.file_text_extractor import FileTextExtractionError, extract_text
from app.services.rag import index_file_chunks

router = APIRouter(prefix="/files", tags=["Files"])

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "text/csv",
    "application/vnd.ms-excel",
}

_MAGIC_PREFIXES: list[tuple[bytes, str]] = [
    (b"\xFF\xD8\xFF", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),
    (b"%PDF", "application/pdf"),
    (b"PK\x03\x04", "application/zip"),
]


def _sniff_content_type(data: bytes, claimed: str | None) -> str | None:
    """يرجع نوعًا مسموحًا بعد فحص التوقيع، أو None لو مشبوه."""
    if not data:
        return None
    for prefix, mime in _MAGIC_PREFIXES:
        if data.startswith(prefix):
            if mime == "application/zip":
                if claimed in {
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                }:
                    return claimed
                return None
            if mime == "image/webp":
                if b"WEBP" in data[:16]:
                    return "image/webp"
                continue
            return mime
    if claimed in {"text/plain", "text/csv", "application/vnd.ms-excel"}:
        sample = data[:2048]
        if b"\x00" in sample:
            return None
        try:
            sample.decode("utf-8")
            return claimed
        except UnicodeDecodeError:
            try:
                sample.decode("latin-1")
                return claimed
            except UnicodeDecodeError:
                return None
    return None


def _validate_office_archive(path: Path, max_uncompressed: int) -> None:
    """Basic ZIP-bomb defense for DOCX/XLSX containers without extracting them."""
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > 1000:
                raise HTTPException(status_code=415, detail="ملف Office يحتوي عددًا غير طبيعي من العناصر")

            total_uncompressed = 0
            for info in infos:
                if info.filename.startswith("/") or ".." in Path(info.filename).parts:
                    raise HTTPException(status_code=415, detail="مسار داخل ملف Office غير صالح")
                if info.file_size > max_uncompressed:
                    raise HTTPException(status_code=415, detail="عنصر داخل ملف Office أكبر من الحد المسموح")
                total_uncompressed += info.file_size
                if total_uncompressed > max_uncompressed:
                    raise HTTPException(status_code=415, detail="الحجم غير المضغوط لملف Office كبير جدًا")
                if info.compress_size and info.file_size / info.compress_size > 100:
                    raise HTTPException(status_code=415, detail="نسبة ضغط غير طبيعية في ملف Office")
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=415, detail="ملف Office تالف أو ليس ZIP صالحًا") from exc


def _user_upload_dir(user_id: int) -> Path:
    path = Path(settings.UPLOAD_DIR) / str(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get_owned_conversation(conversation_id: int, current_user: User, db: Session) -> Conversation:
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المحادثة غير موجودة")
    return conversation


def _get_owned_file(file_id: int, current_user: User, db: Session) -> FileAttachment:
    file = (
        db.query(FileAttachment)
        .filter(FileAttachment.id == file_id, FileAttachment.user_id == current_user.id)
        .first()
    )
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملف غير موجود")
    return file


@router.post("/upload", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile,
    conversation_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if conversation_id is not None:
        _get_owned_conversation(conversation_id, current_user, db)

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    max_storage = settings.MAX_STORAGE_PER_USER_MB * 1024 * 1024
    current_files = db.query(func.count(FileAttachment.id)).filter(FileAttachment.user_id == current_user.id).scalar() or 0
    if current_files >= settings.MAX_FILES_PER_USER:
        raise HTTPException(status_code=413, detail="وصلت للحد الأقصى لعدد الملفات")
    current_storage = db.query(func.coalesce(func.sum(FileAttachment.size_bytes), 0)).filter(FileAttachment.user_id == current_user.id).scalar() or 0

    extension = Path(file.filename or "").suffix.lower()
    stored_filename = f"{uuid.uuid4().hex}{extension}"
    destination = _user_upload_dir(current_user.id) / stored_filename
    temp_path = None
    total = 0
    header = bytearray()
    sniffed = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".upload-", delete=False) as tmp:
            temp_path = Path(tmp.name)
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(status_code=413, detail=f"الملف أكبر من الحد المسموح ({settings.MAX_UPLOAD_SIZE_MB} ميجابايت)")
                if current_storage + total > max_storage:
                    raise HTTPException(status_code=413, detail=f"تجاوزت سعة التخزين للحساب ({settings.MAX_STORAGE_PER_USER_MB} ميجابايت)")
                if len(header) < 4096:
                    header.extend(chunk[: 4096 - len(header)])
                tmp.write(chunk)

        sniffed = _sniff_content_type(bytes(header), file.content_type)
        if sniffed is None or sniffed not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=415, detail="نوع الملف غير مدعوم أو لا يطابق محتواه (مسموح: صور، PDF، Word، Excel، CSV)")

        if sniffed in {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }:
            _validate_office_archive(temp_path, max_uncompressed=max_bytes)

        temp_path.replace(destination)
        temp_path = None
    finally:
        if temp_path:
            temp_path.unlink(missing_ok=True)

    extracted_text = None
    if sniffed is not None:
        try:
            extracted_text = extract_text(destination, sniffed)
        except FileTextExtractionError as exc:
            log_event(
                db,
                "file_text_extraction_failed",
                f"فشل استخراج نص الملف: {file.filename or stored_filename} ({exc})",
                current_user.id,
            )

    attachment = FileAttachment(
        user_id=current_user.id,
        original_filename=(file.filename or stored_filename)[:255],
        stored_filename=stored_filename,
        content_type=sniffed,
        size_bytes=total,
        extracted_text=extracted_text,
    )
    db.add(attachment)
    db.flush()

    if extracted_text:
        try:
            indexed_chunks = index_file_chunks(db, attachment)
            if indexed_chunks:
                log_event(
                    db,
                    "file_rag_indexed",
                    f"تم فهرسة {indexed_chunks} مقطعًا للملف {attachment.original_filename}",
                    current_user.id,
                )
        except EmbeddingServiceError as exc:
            log_event(
                db,
                "file_rag_index_failed",
                f"تعذر فهرسة الملف {attachment.original_filename}: {exc}",
                current_user.id,
            )

    if conversation_id is not None:
        db.add(
            ConversationFileLink(
                conversation_id=conversation_id,
                file_id=attachment.id,
            )
        )
    db.commit()
    db.refresh(attachment)
    log_event(
        db,
        "file_uploaded",
        f"رفع ملف: {attachment.original_filename} بواسطة {current_user.email}",
        current_user.id,
    )
    response = FileOut.model_validate(attachment)
    response.is_attached = conversation_id is not None
    return response


@router.get("", response_model=list[FileOut])
def list_files(
    conversation_id: int | None = None,
    include_unattached: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if conversation_id is None:
        return (
            db.query(FileAttachment)
            .filter(FileAttachment.user_id == current_user.id)
            .order_by(FileAttachment.created_at.desc())
            .all()
        )

    _get_owned_conversation(conversation_id, current_user, db)

    if not include_unattached:
        files = (
            db.query(FileAttachment)
            .join(
                ConversationFileLink,
                and_(
                    ConversationFileLink.file_id == FileAttachment.id,
                    ConversationFileLink.conversation_id == conversation_id,
                ),
            )
            .filter(FileAttachment.user_id == current_user.id)
            .order_by(FileAttachment.created_at.desc())
            .all()
        )
        results = []
        for file in files:
            item = FileOut.model_validate(file)
            item.is_attached = True
            results.append(item)
        return results

    rows = (
        db.query(
            FileAttachment,
            case(
                (ConversationFileLink.file_id.isnot(None), True),
                else_=False,
            ).label("is_attached"),
        )
        .outerjoin(
            ConversationFileLink,
            and_(
                ConversationFileLink.file_id == FileAttachment.id,
                ConversationFileLink.conversation_id == conversation_id,
            ),
        )
        .filter(FileAttachment.user_id == current_user.id)
        .order_by(FileAttachment.created_at.desc())
        .all()
    )
    results = []
    for file, is_attached in rows:
        item = FileOut.model_validate(file)
        item.is_attached = bool(is_attached)
        results.append(item)
    return results


@router.post("/{file_id}/attach/{conversation_id}", response_model=FileOut)
def attach_file_to_conversation(
    file_id: int,
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    file = _get_owned_file(file_id, current_user, db)
    _get_owned_conversation(conversation_id, current_user, db)
    link = (
        db.query(ConversationFileLink)
        .filter(
            ConversationFileLink.file_id == file.id,
            ConversationFileLink.conversation_id == conversation_id,
        )
        .first()
    )
    if not link:
        db.add(
            ConversationFileLink(
                file_id=file.id,
                conversation_id=conversation_id,
            )
        )
        db.commit()
    response = FileOut.model_validate(file)
    response.is_attached = True
    return response


@router.delete("/{file_id}/attach/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def detach_file_from_conversation(
    file_id: int,
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    file = _get_owned_file(file_id, current_user, db)
    _get_owned_conversation(conversation_id, current_user, db)
    link = (
        db.query(ConversationFileLink)
        .filter(
            ConversationFileLink.file_id == file.id,
            ConversationFileLink.conversation_id == conversation_id,
        )
        .first()
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الملف غير مرفق بهذه المحادثة",
        )
    db.delete(link)
    db.commit()


@router.get("/{file_id}")
def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attachment = _get_owned_file(file_id, current_user, db)
    path = _user_upload_dir(current_user.id) / attachment.stored_filename
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملف غير موجود على القرص")
    return FileResponse(
        path, media_type=attachment.content_type, filename=attachment.original_filename
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attachment = _get_owned_file(file_id, current_user, db)
    path = _user_upload_dir(current_user.id) / attachment.stored_filename
    path.unlink(missing_ok=True)
    db.delete(attachment)
    db.commit()
    log_event(
        db,
        "file_deleted",
        f"حذف ملف: {attachment.original_filename} بواسطة {current_user.email}",
        current_user.id,
    )
