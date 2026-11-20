"""Transactional enqueue helpers for durable object-storage cleanup."""
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.storage_cleanup_outbox import StorageCleanupOutbox

logger = logging.getLogger(__name__)


def enqueue_user_storage_cleanup(db: Session, user_id: int) -> StorageCleanupOutbox:
    """Add a prefix cleanup instruction to the caller's current transaction."""
    row = StorageCleanupOutbox(
        user_id=user_id,
        operation="delete_user_prefix",
        status="pending",
    )
    db.add(row)
    return row


def enqueue_file_storage_cleanup(
    db: Session,
    object_key: str,
    fallback_path: Path,
) -> StorageCleanupOutbox:
    """Add a single-object cleanup instruction using a safe relative path."""
    root = Path(settings.UPLOAD_DIR).resolve()
    resolved = Path(fallback_path).resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("Fallback cleanup path must stay inside UPLOAD_DIR") from exc
    row = StorageCleanupOutbox(
        operation="delete_file",
        object_key=object_key,
        fallback_path=relative.as_posix(),
        status="pending",
    )
    db.add(row)
    return row


def record_file_cleanup_failure(object_key: str, fallback_path: Path) -> None:
    """Persist cleanup after the upload transaction has already rolled back."""
    db = SessionLocal()
    try:
        enqueue_file_storage_cleanup(db, object_key, fallback_path)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "Could not persist storage cleanup outbox entry for %s",
            object_key,
        )
    finally:
        db.close()


def dispatch_storage_cleanup() -> None:
    """Best-effort immediate wake-up; the Celery Beat poll is the durable fallback."""
    try:
        from app.tasks import process_storage_cleanup_outbox

        if process_storage_cleanup_outbox is not None:
            process_storage_cleanup_outbox.delay()
    except Exception:
        logger.exception("Could not dispatch storage cleanup worker; outbox remains pending")
