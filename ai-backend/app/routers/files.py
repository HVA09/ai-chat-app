"""
مسارات رفع الملفات وإدارتها: صور، PDF، Word، Excel، CSV
تُخزَّن الملفات على القرص (مجلد UPLOAD_DIR) والبيانات الوصفية بقاعدة البيانات
"""
import base64
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
from app.dependencies import enforce_daily_ai_limit, enforce_workspace_daily_ai_limit, get_allowed_ai_models, get_current_user
from app.audit import log_event
from app.models.conversation import Conversation
from app.models.conversation_file_link import ConversationFileLink
from app.models.file_attachment import FileAttachment
from app.models.file_chunk import FileChunk
from app.models.project import WorkspaceProject
from app.models.usage_log import UsageLog
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.file import FileOut
from app.services.embeddings import EmbeddingServiceError
from app.services.file_text_extractor import FileTextExtractionError, extract_text
from app.services.rag import index_file_chunks
from app.services.image_rag import index_image_file

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


def _get_accessible_project(
    project_id: int, current_user: User, db: Session
) -> WorkspaceProject:
    project = db.get(WorkspaceProject, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المشروع غير موجود")
    _get_workspace_membership(project.workspace_id, current_user, db)
    return project


def _get_workspace_membership(
    workspace_id: int, current_user: User, db: Session
) -> WorkspaceMember:
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
    return membership


def _get_accessible_file(
    file_id: int, current_user: User, db: Session
) -> FileAttachment:
    file = db.query(FileAttachment).filter(FileAttachment.id == file_id).first()
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملف غير موجود")

    if file.workspace_id is None:
        if file.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملف غير موجود")
        return file

    _get_workspace_membership(file.workspace_id, current_user, db)
    return file


def _file_response(
    file: FileAttachment,
    current_user: User,
    db: Session,
    *,
    is_attached: bool = False,
) -> FileOut:
    response = FileOut.model_validate(file)
    response.is_attached = is_attached
    response.workspace_id = file.workspace_id
    response.is_owner = file.user_id == current_user.id

    can_delete = response.is_owner
    if file.workspace_id is not None and not can_delete:
        membership = _get_workspace_membership(file.workspace_id, current_user, db)
        can_delete = membership.role in {WorkspaceRole.owner, WorkspaceRole.admin}
    response.can_delete = can_delete
    has_embedding = bool(
        db.query(FileChunk.id)
        .filter(
            FileChunk.file_id == file.id,
            FileChunk.embedding.is_not(None),
        )
        .first()
    )
    response.is_ai_indexed = has_embedding or (
        file.content_type.startswith("image/") and file.extracted_text is not None
    )
    return response


@router.post("/upload", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile,
    conversation_id: int | None = None,
    workspace_id: int | None = None,
    project_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = None
    if project_id is not None:
        project = _get_accessible_project(project_id, current_user, db)
        if workspace_id is not None and workspace_id != project.workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="مساحة العمل لا تطابق مساحة عمل المشروع",
            )
        workspace_id = project.workspace_id

    if conversation_id is not None:
        conversation = _get_owned_conversation(conversation_id, current_user, db)
        if workspace_id is not None and workspace_id != conversation.workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="مساحة العمل لا تطابق مساحة عمل المحادثة",
            )
        if project_id is not None and conversation.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="المشروع لا يطابق مشروع المحادثة",
            )
    if workspace_id is not None:
        _get_workspace_membership(workspace_id, current_user, db)

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
        workspace_id=workspace_id,
        project_id=project_id,
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
    return _file_response(
        attachment,
        current_user,
        db,
        is_attached=conversation_id is not None,
    )


@router.get("", response_model=list[FileOut])
def list_files(
    conversation_id: int | None = None,
    include_unattached: bool = False,
    workspace_id: int | None = None,
    project_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if project_id is not None:
        project = _get_accessible_project(project_id, current_user, db)
        files = (
            db.query(FileAttachment)
            .filter(FileAttachment.project_id == project.id)
            .order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc())
            .all()
        )
        return [
            _file_response(file, current_user, db)
            for file in files
        ]

    if workspace_id is not None:
        _get_workspace_membership(workspace_id, current_user, db)
        files = (
            db.query(FileAttachment)
            .filter(FileAttachment.workspace_id == workspace_id)
            .order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc())
            .all()
        )
        return [_file_response(file, current_user, db) for file in files]

    if conversation_id is None:
        files = (
            db.query(FileAttachment)
            .filter(
                FileAttachment.user_id == current_user.id,
                FileAttachment.workspace_id.is_(None),
            )
            .order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc())
            .all()
        )
        return [_file_response(file, current_user, db) for file in files]

    conversation = _get_owned_conversation(conversation_id, current_user, db)

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
            results.append(_file_response(file, current_user, db, is_attached=True))
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
        .filter(
            FileAttachment.user_id == current_user.id,
            FileAttachment.workspace_id.is_(None),
        )
        .order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc())
        .all()
    )
    results = []
    for file, is_attached in rows:
        results.append(
            _file_response(file, current_user, db, is_attached=bool(is_attached))
        )
    return results


@router.post("/{file_id}/attach/{conversation_id}", response_model=FileOut)
def attach_file_to_conversation(
    file_id: int,
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    file = _get_accessible_file(file_id, current_user, db)
    conversation = _get_owned_conversation(conversation_id, current_user, db)
    if file.project_id is not None and file.project_id != conversation.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ملف المشروع لا ينتمي إلى مشروع المحادثة",
        )
    if file.workspace_id is not None and file.workspace_id != conversation.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ملف مساحة العمل لا ينتمي إلى مساحة عمل المحادثة",
        )
    if file.project_id is not None and file.project_id != conversation.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ملف المشروع لا ينتمي إلى مشروع المحادثة",
        )

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
    return _file_response(file, current_user, db, is_attached=True)


@router.delete("/{file_id}/attach/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def detach_file_from_conversation(
    file_id: int,
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    file = _get_accessible_file(file_id, current_user, db)
    conversation = _get_owned_conversation(conversation_id, current_user, db)
    if file.workspace_id is not None and file.workspace_id != conversation.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ملف مساحة العمل لا ينتمي إلى مساحة عمل المحادثة",
        )
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
    attachment = _get_accessible_file(file_id, current_user, db)
    path = _user_upload_dir(attachment.user_id) / attachment.stored_filename
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملف غير موجود على القرص")
    return FileResponse(
        path, media_type=attachment.content_type, filename=attachment.original_filename
    )


@router.post("/{file_id}/index-image", response_model=FileOut)
async def index_image_for_rag(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """يفهرس صورة صراحةً في RAG بدون استدعاء Vision مخفي أثناء كل رسالة."""
    attachment = _get_accessible_file(file_id, current_user, db)

    if not attachment.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="يمكن فهرسة الصور فقط",
        )

    if attachment.extracted_text:
        return _file_response(attachment, current_user, db)

    enforce_daily_ai_limit(current_user, db)

    if attachment.workspace_id is not None:
        enforce_workspace_daily_ai_limit(attachment.workspace_id, current_user, db)

    allowed_models = get_allowed_ai_models(current_user, db)
    model = allowed_models[0] if allowed_models else settings.AI_MODEL

    try:
        reply, indexed_chunks = await index_image_file(attachment, db, model)
    except (FileNotFoundError, ValueError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    db.add(
        UsageLog(
            user_id=current_user.id,
            workspace_id=attachment.workspace_id,
            endpoint="/files/index-image",
            model=model,
            provider=reply.provider,
            input_tokens=reply.input_tokens,
            output_tokens=reply.output_tokens,
            latency_ms=reply.latency_ms,
        )
    )
    db.commit()
    db.refresh(attachment)

    log_event(
        db,
        "file_rag_indexed",
        f"فهرسة صورة للـ RAG: {attachment.original_filename} ({indexed_chunks} مقطع)",
        current_user.id,
    )
    return _file_response(attachment, current_user, db)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attachment = _get_accessible_file(file_id, current_user, db)
    if not _file_response(attachment, current_user, db).can_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ليس لديك صلاحية حذف هذا الملف",
        )
    path = _user_upload_dir(attachment.user_id) / attachment.stored_filename
    path.unlink(missing_ok=True)
    db.delete(attachment)
    db.commit()
    log_event(
        db,
        "file_deleted",
        f"حذف ملف: {attachment.original_filename} بواسطة {current_user.email}",
        current_user.id,
    )
