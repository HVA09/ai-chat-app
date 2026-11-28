"""Transactional enqueue and bookkeeping for failed upload-object cleanup.

No background worker is enabled here. A pending row is durable recovery intent;
lease expiry or object age never authorizes a destructive cleanup.
"""
import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.file_attachment import FileAttachment
from app.models.upload_cleanup_intent import UploadCleanupIntent
from app.models.user import User


def _idempotency_key(object_key: str) -> str:
    return hashlib.sha256(
        ("upload-object-cleanup:v1:" + object_key).encode("utf-8")
    ).hexdigest()


def enqueue_upload_cleanup_intent(
    db: Session,
    *,
    user_id: int | None,
    object_key: str,
    lease_id: str | None = None,
    generation: int | None = None,
) -> UploadCleanupIntent | None:
    """Persist a cleanup request, returning None if a committed attachment owns the key.

    The caller owns the transaction and must commit before attempting storage
    deletion. Lock order is User -> FileAttachment, matching upload/account
    retention serialization. If the user was already deleted, the intent
    remains ownerless and the attachment ownership check still fails closed.
    """
    if not object_key or len(object_key) > 512 or object_key.startswith("/"):
        raise ValueError("object_key is invalid")

    persisted_user_id = user_id
    if user_id is not None:
        locked_user = (
            db.query(User.id)
            .filter(User.id == user_id)
            .with_for_update()
            .first()
        )
        if locked_user is None:
            persisted_user_id = None

    committed_attachment = (
        db.query(FileAttachment.id)
        .filter(FileAttachment.object_key == object_key)
        .with_for_update()
        .first()
    )
    if committed_attachment is not None:
        return None

    key = _idempotency_key(object_key)
    existing = (
        db.query(UploadCleanupIntent)
        .filter(UploadCleanupIntent.idempotency_key == key)
        .with_for_update()
        .first()
    )
    if existing is not None:
        return existing

    intent = UploadCleanupIntent(
        id=str(uuid.uuid4()),
        idempotency_key=key,
        user_id=persisted_user_id,
        lease_id=lease_id,
        generation=generation,
        object_key=object_key,
        status="pending",
        attempt_count=0,
        next_attempt_at=datetime.now(timezone.utc),
    )
    # Isolate the unique-key race in a SAVEPOINT. A full Session.rollback()
    # would also discard unrelated work owned by the caller.
    try:
        with db.begin_nested():
            db.add(intent)
            db.flush()
    except IntegrityError:
        # A concurrent ownerless enqueue can race when account deletion has
        # already removed the User row (and therefore its serialization lock).
        existing = (
            db.query(UploadCleanupIntent)
            .filter(UploadCleanupIntent.idempotency_key == key)
            .first()
        )
        if existing is not None:
            return existing
        raise
    return intent


def record_upload_cleanup_attempt(
    db: Session,
    *,
    intent_id: str,
    succeeded: bool,
    error_code: str | None = None,
) -> bool:
    """Record one immediate storage attempt; never reopens a completed intent."""
    now = datetime.now(timezone.utc)
    values = {
        "attempt_count": UploadCleanupIntent.attempt_count + 1,
        "last_error_code": None if succeeded else (error_code or "storage_error")[:64],
        "updated_at": now,
    }
    if succeeded:
        values.update(status="completed", completed_at=now)
    else:
        values.update(status="pending", completed_at=None)
    result = db.execute(
        update(UploadCleanupIntent)
        .where(
            UploadCleanupIntent.id == intent_id,
            UploadCleanupIntent.status == "pending",
        )
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1
