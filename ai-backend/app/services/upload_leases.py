"""Compare-and-swap operations for durable upload lease ownership.

These helpers never commit. Callers must include lease state changes and any
FileAttachment finalization in the same SQLAlchemy transaction.
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.upload_lease import UploadLease


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_upload_lease(
    db: Session,
    *,
    user_id: int,
    object_key: str,
    staging_key: str | None = None,
) -> tuple[UploadLease, str]:
    """Create ingress ownership before any managed object is written.

    The caller must hold the same user-row lock used by account deletion.
    """
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    lease = UploadLease(
        id=str(uuid.uuid4()),
        user_id=user_id,
        object_key=object_key,
        staging_key=staging_key,
        status="receiving",
        generation=1,
        owner_token_hash=_token_hash(token),
        heartbeat_at=now,
    )
    db.add(lease)
    db.flush()
    return lease, token


def queue_upload_lease(
    db: Session, *, lease_id: str, generation: int, owner_token: str
) -> bool:
    """Move a fully received ingress lease to the durable worker queue."""
    result = db.execute(
        update(UploadLease)
        .where(
            UploadLease.id == lease_id,
            UploadLease.generation == generation,
            UploadLease.owner_token_hash == _token_hash(owner_token),
            UploadLease.status == "receiving",
        )
        .values(status="queued", heartbeat_at=datetime.now(timezone.utc))
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


def claim_upload_lease(
    db: Session, *, lease_id: str, lease_seconds: int
) -> tuple[int, str] | None:
    """Atomically claim queued work and advance its fencing generation.

    Expired processing leases are intentionally not reclaimable here. A
    timeout is not proof that a previous worker has stopped making side effects.
    """
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    result = db.execute(
        update(UploadLease)
        .where(UploadLease.id == lease_id, UploadLease.status == "queued")
        .values(
            status="processing",
            generation=UploadLease.generation + 1,
            owner_token_hash=_token_hash(token),
            heartbeat_at=now,
            expires_at=now + timedelta(seconds=lease_seconds),
            updated_at=now,
        )
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        return None
    lease = db.get(UploadLease, lease_id, populate_existing=True)
    if lease is None:
        return None
    return lease.generation, token


def heartbeat_upload_lease(
    db: Session,
    *,
    lease_id: str,
    generation: int,
    owner_token: str,
    lease_seconds: int,
) -> bool:
    """Renew only the current processing owner; expiry is not delete authority."""
    now = datetime.now(timezone.utc)
    result = db.execute(
        update(UploadLease)
        .where(
            UploadLease.id == lease_id,
            UploadLease.status == "processing",
            UploadLease.generation == generation,
            UploadLease.owner_token_hash == _token_hash(owner_token),
        )
        .values(
            heartbeat_at=now,
            expires_at=now + timedelta(seconds=lease_seconds),
            updated_at=now,
        )
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


def mark_upload_lease_cleanup_pending(
    db: Session, *, lease_id: str, generation: int, owner_token: str
) -> bool:
    """Persist recovery intent without deleting any local or remote object."""
    result = db.execute(
        update(UploadLease)
        .where(
            UploadLease.id == lease_id,
            UploadLease.status.in_(("receiving", "queued", "processing")),
            UploadLease.generation == generation,
            UploadLease.owner_token_hash == _token_hash(owner_token),
        )
        .values(
            status="cleanup_pending",
            owner_token_hash=None,
            expires_at=None,
            updated_at=datetime.now(timezone.utc),
        )
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


def finalize_upload_lease(
    db: Session,
    *,
    lease_id: str,
    generation: int,
    owner_token: str,
    attachment_id: int,
) -> bool:
    """Commit lease metadata alongside the attachment in the caller's transaction."""
    result = db.execute(
        update(UploadLease)
        .where(
            UploadLease.id == lease_id,
            UploadLease.status == "processing",
            UploadLease.generation == generation,
            UploadLease.owner_token_hash == _token_hash(owner_token),
        )
        .values(
            status="committed",
            attachment_id=attachment_id,
            owner_token_hash=None,
            expires_at=None,
            updated_at=datetime.now(timezone.utc),
        )
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1
