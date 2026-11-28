"""Transactional reader leases for attachment content access."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event, Thread
from typing import Iterator
from uuid import uuid4

from sqlalchemy import delete, select, text, update
from sqlalchemy.orm import Session

from app.database import SessionLocal, commit_and_release_connection
from app.models.file_attachment import FileAttachment
from app.models.file_attachment_read_lease import FileAttachmentReadLease
from app.models.user import User


class FileUnavailableError(RuntimeError):
    """The attachment is missing or has entered deletion."""


class ActiveFileReadLeaseError(RuntimeError):
    """Physical cleanup must wait for an active reader."""


def acquire_file_read_lease(file_id: int, db: Session, lease_seconds: int = 900) -> str:
    """Acquire a bounded lease in the request transaction under the delete row lock."""
    lease_id = str(uuid4())
    # Account deletion takes the User row lock before it cascades attachment
    # metadata. Take that same lock first so a reader cannot slip between the
    # account-delete flush and its commit. The owner lookup is only a hint:
    # revalidate the attachment after acquiring the owner lock.
    owner_id = (
        db.query(FileAttachment.user_id)
        .filter(FileAttachment.id == file_id)
        .scalar()
    )
    if owner_id is None:
        raise FileUnavailableError("File is unavailable for reading")
    owner_exists = (
        db.query(User.id)
        .filter(User.id == owner_id)
        .with_for_update()
        .first()
    )
    if owner_exists is None:
        raise FileUnavailableError("File is unavailable for reading")
    attachment = (
        db.query(FileAttachment)
        .filter(FileAttachment.id == file_id, FileAttachment.user_id == owner_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if attachment is None or attachment.deletion_status != "available":
        raise FileUnavailableError("File is unavailable for reading")
    db.add(
        FileAttachmentReadLease(
            id=lease_id,
            file_attachment_id=file_id,
            user_id=attachment.user_id,
            expires_at=datetime.now(timezone.utc)
            + timedelta(seconds=max(30, min(lease_seconds, 3600))),
        )
    )
    return lease_id


def release_file_read_lease(lease_id: str) -> None:
    db: Session = SessionLocal()
    try:
        db.execute(delete(FileAttachmentReadLease).where(FileAttachmentReadLease.id == lease_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def renew_file_read_lease(lease_id: str, lease_seconds: int = 900) -> bool:
    """Renew only the matching lease while it is still valid; stale owners cannot revive it."""
    db: Session = SessionLocal()
    instant = datetime.now(timezone.utc)
    expiry = instant + timedelta(seconds=max(30, min(lease_seconds, 3600)))
    try:
        # A heartbeat must fail well before its 15-minute lease can expire.
        # The engine also bounds pool checkout and PostgreSQL connection setup.
        if db.get_bind().dialect.name == "postgresql":
            db.execute(text("SET LOCAL statement_timeout = '10s'"))
        result = db.execute(
            update(FileAttachmentReadLease)
            .where(FileAttachmentReadLease.id == lease_id, FileAttachmentReadLease.expires_at > instant)
            .values(expires_at=expiry)
        )
        db.commit()
        return result.rowcount == 1
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()



def stream_file_with_lease(body, lease_id: str, heartbeat_interval: float = 30.0) -> Iterator[bytes]:
    """Keep a lease alive independently of storage reads and client backpressure."""
    stopped = Event()
    lease_lost = Event()

    def heartbeat() -> None:
        while not stopped.wait(heartbeat_interval):
            try:
                if not renew_file_read_lease(lease_id):
                    lease_lost.set()
                    close = getattr(body, "close", None)
                    if callable(close):
                        try:
                            close()
                        except Exception:
                            pass
                    return
            except Exception:
                # Fail closed: stop the underlying stream rather than let cleanup
                # proceed on an expired lease while a reader may still be active.
                lease_lost.set()
                close = getattr(body, "close", None)
                if callable(close):
                    try:
                        close()
                    except Exception:
                        pass
                return

    worker = Thread(target=heartbeat, name="file-read-lease-heartbeat", daemon=True)
    worker.start()
    try:
        for chunk in body:
            if lease_lost.is_set():
                raise RuntimeError("File read lease could not be renewed")
            yield chunk
        if lease_lost.is_set():
            raise RuntimeError("File read lease could not be renewed")
    finally:
        stopped.set()
        close = getattr(body, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass
        worker.join(timeout=2.0)
        # Never drop the protection while a heartbeat operation may still be
        # in flight. If the worker cannot stop promptly, leave the bounded
        # lease to expire naturally; cleanup will defer until then.
        if not worker.is_alive():
            release_file_read_lease(lease_id)

@contextmanager
def leased_materialize_file(
    attachment: FileAttachment,
    db: Session,
    fallback_path: Path,
) -> Iterator[Path]:
    """Protect storage reads until the attachment has been materialized and consumed."""
    lease_id = acquire_file_read_lease(attachment.id, db)
    try:
        # Persist the lease before any potentially slow object-storage operation.
        commit_and_release_connection(db)
        from app.services.storage import materialize_file

        with materialize_file(attachment.object_key, fallback_path) as path:
            yield path
    finally:
        release_file_read_lease(lease_id)

def has_active_file_read_leases(file_id: int, now: datetime | None = None) -> bool:
    db: Session = SessionLocal()
    try:
        instant = now or datetime.now(timezone.utc)
        # Expired leases no longer protect storage and should not accumulate
        # indefinitely when a client disconnects without a clean close.
        db.execute(
            delete(FileAttachmentReadLease).where(
                FileAttachmentReadLease.file_attachment_id == file_id,
                FileAttachmentReadLease.expires_at <= instant,
            )
        )
        db.commit()
        return db.execute(
            select(FileAttachmentReadLease.id)
            .where(
                FileAttachmentReadLease.file_attachment_id == file_id,
                FileAttachmentReadLease.expires_at > instant,
            )
            .limit(1)
        ).first() is not None
    finally:
        db.close()


def has_active_user_read_leases(user_id: int, now: datetime | None = None) -> bool:
    """Return whether any unexpired reader lease remains for a deleted user's objects."""
    db: Session = SessionLocal()
    try:
        instant = now or datetime.now(timezone.utc)
        db.execute(
            delete(FileAttachmentReadLease).where(
                FileAttachmentReadLease.user_id == user_id,
                FileAttachmentReadLease.expires_at <= instant,
            )
        )
        db.commit()
        return db.execute(
            select(FileAttachmentReadLease.id)
            .where(
                FileAttachmentReadLease.user_id == user_id,
                FileAttachmentReadLease.expires_at > instant,
            )
            .limit(1)
        ).first() is not None
    finally:
        db.close()
