"""Transactional state transitions for durable upload-processing jobs.

These helpers never commit. Callers own the transaction that also persists
any stage result. Lock order is always User -> UploadLease -> UploadProcessingJob.
An expired processing lease is deliberately not reclaimable: expiry is not
proof that the previous worker process has terminated.
"""
import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.upload_lease import UploadLease
from app.models.upload_processing_job import UploadProcessingJob
from app.models.user import User


_VALID_STAGES = {"extract", "index"}
_SAFE_ERROR_CODE = re.compile(r"^[a-z0-9_.-]{1,64}$")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _lock_owner_and_lease(db: Session, lease_id: str) -> tuple[User, UploadLease] | None:
    # The initial unlocked read is only a locator. Revalidate after taking
    # locks in the globally documented User -> Lease order.
    locator = db.execute(
        select(UploadLease.user_id).where(UploadLease.id == lease_id)
    ).scalar_one_or_none()
    if locator is None:
        return None
    user = db.execute(
        select(User).where(User.id == locator).with_for_update()
    ).scalar_one_or_none()
    if user is None:
        return None
    lease = db.execute(
        select(UploadLease).where(UploadLease.id == lease_id).with_for_update()
    ).scalar_one_or_none()
    if lease is None or lease.user_id != user.id:
        return None
    return user, lease


def _lock_job(db: Session, job_id: str) -> UploadProcessingJob | None:
    return db.execute(
        select(UploadProcessingJob).where(
            UploadProcessingJob.id == job_id
        ).with_for_update()
    ).scalar_one_or_none()


def _owned_job(
    db: Session, *, job_id: str, generation: int, owner_token: str
) -> UploadProcessingJob | None:
    locator = db.execute(
        select(UploadProcessingJob.lease_id).where(UploadProcessingJob.id == job_id)
    ).scalar_one_or_none()
    if locator is None or _lock_owner_and_lease(db, locator) is None:
        return None
    job = _lock_job(db, job_id)
    if (
        job is None
        or job.status != "processing"
        or job.generation != generation
        or job.owner_token_hash != _hash_token(owner_token)
    ):
        return None
    return job


def create_upload_processing_job(
    db: Session, *, lease_id: str, stage: str, stage_revision: int = 1,
    max_attempts: int = 4,
) -> tuple[UploadProcessingJob, bool]:
    """Create one durable outbox row; return (job, created).

    Caller must keep this transaction atomic with the lease transition that
    makes this stage eligible. Repeated calls with the same idempotency key
    return the existing row without creating duplicate work.
    """
    if stage not in _VALID_STAGES:
        raise ValueError("stage must be 'extract' or 'index'")
    if stage_revision <= 0:
        raise ValueError("stage_revision must be positive")
    if max_attempts <= 0:
        raise ValueError("max_attempts must be positive")
    locked = _lock_owner_and_lease(db, lease_id)
    if locked is None:
        raise ValueError("upload lease has no active owner")
    _, lease = locked
    if lease.status not in {"queued", "processing", "committed"}:
        raise ValueError("upload lease is not eligible for processing")
    existing = db.execute(
        select(UploadProcessingJob).where(
            UploadProcessingJob.lease_id == lease_id,
            UploadProcessingJob.stage == stage,
            UploadProcessingJob.stage_revision == stage_revision,
        ).with_for_update()
    ).scalar_one_or_none()
    if existing is not None:
        return existing, False
    job = UploadProcessingJob(
        id=str(uuid.uuid4()),
        lease_id=lease_id,
        stage=stage,
        stage_revision=stage_revision,
        status="pending_dispatch",
        max_attempts=max_attempts,
    )
    db.add(job)
    db.flush()
    return job, True


def queue_upload_processing_job(db: Session, *, job_id: str) -> bool:
    """Promote a due outbox/retry row for broker delivery; no broker I/O here."""
    locator = db.execute(
        select(UploadProcessingJob.lease_id).where(UploadProcessingJob.id == job_id)
    ).scalar_one_or_none()
    if locator is None or _lock_owner_and_lease(db, locator) is None:
        return False
    job = _lock_job(db, job_id)
    now = datetime.now(timezone.utc)
    if (
        job is None
        or job.status not in {"pending_dispatch", "retry_wait"}
        or job.available_at > now
    ):
        return False
    job.status = "queued"
    job.updated_at = now
    db.flush()
    return True


def claim_upload_processing_job(
    db: Session, *, job_id: str, lease_seconds: int = 120
) -> tuple[int, str] | None:
    """Claim a queued job with a fresh fencing generation and secret token."""
    if lease_seconds <= 0:
        raise ValueError("lease_seconds must be positive")
    locator = db.execute(
        select(UploadProcessingJob.lease_id).where(UploadProcessingJob.id == job_id)
    ).scalar_one_or_none()
    if locator is None or _lock_owner_and_lease(db, locator) is None:
        return None
    job = _lock_job(db, job_id)
    now = datetime.now(timezone.utc)
    if job is None or job.status != "queued" or job.available_at > now:
        return None
    if job.attempt_count >= job.max_attempts:
        job.status = "failed_terminal"
        job.completed_at = now
        job.owner_token_hash = None
        job.expires_at = None
        job.updated_at = now
        db.flush()
        return None
    token = secrets.token_urlsafe(32)
    job.status = "processing"
    job.generation += 1
    job.owner_token_hash = _hash_token(token)
    job.attempt_count += 1
    job.heartbeat_at = now
    job.expires_at = now + timedelta(seconds=lease_seconds)
    job.started_at = job.started_at or now
    job.updated_at = now
    db.flush()
    return job.generation, token


def heartbeat_upload_processing_job(
    db: Session, *, job_id: str, generation: int, owner_token: str,
    lease_seconds: int = 120,
) -> bool:
    if lease_seconds <= 0:
        raise ValueError("lease_seconds must be positive")
    job = _owned_job(db, job_id=job_id, generation=generation, owner_token=owner_token)
    if job is None:
        return False
    now = datetime.now(timezone.utc)
    job.heartbeat_at = now
    job.expires_at = now + timedelta(seconds=lease_seconds)
    job.updated_at = now
    db.flush()
    return True


def complete_upload_processing_job(
    db: Session, *, job_id: str, generation: int, owner_token: str,
) -> bool:
    """Mark success in the caller's transaction with its durable stage result."""
    job = _owned_job(db, job_id=job_id, generation=generation, owner_token=owner_token)
    if job is None:
        return False
    now = datetime.now(timezone.utc)
    job.status = "succeeded"
    job.owner_token_hash = None
    job.expires_at = None
    job.completed_at = now
    job.updated_at = now
    db.flush()
    return True


def retry_upload_processing_job(
    db: Session, *, job_id: str, generation: int, owner_token: str,
    error_code: str, delay_seconds: int,
) -> bool:
    """Schedule a classified transient failure; dispatcher must republish later."""
    if not _SAFE_ERROR_CODE.fullmatch(error_code):
        raise ValueError("error_code must be a safe lowercase code")
    if delay_seconds < 0:
        raise ValueError("delay_seconds must be nonnegative")
    job = _owned_job(db, job_id=job_id, generation=generation, owner_token=owner_token)
    if job is None:
        return False
    now = datetime.now(timezone.utc)
    job.owner_token_hash = None
    job.expires_at = None
    job.last_error_code = error_code
    job.status = "failed_terminal" if job.attempt_count >= job.max_attempts else "retry_wait"
    job.available_at = now + timedelta(seconds=delay_seconds)
    if job.status == "failed_terminal":
        job.completed_at = now
    job.updated_at = now
    db.flush()
    return True


def fail_upload_processing_job(
    db: Session, *, job_id: str, generation: int, owner_token: str,
    error_code: str,
) -> bool:
    if not _SAFE_ERROR_CODE.fullmatch(error_code):
        raise ValueError("error_code must be a safe lowercase code")
    job = _owned_job(db, job_id=job_id, generation=generation, owner_token=owner_token)
    if job is None:
        return False
    now = datetime.now(timezone.utc)
    job.status = "failed_terminal"
    job.owner_token_hash = None
    job.expires_at = None
    job.last_error_code = error_code
    job.completed_at = now
    job.updated_at = now
    db.flush()
    return True
