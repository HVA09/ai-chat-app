"""Bounded at-least-once dispatch for durable upload-processing jobs.

The job row is the outbox record. The dispatcher locks a due row, publishes
its ID, and only then marks it queued in the same database transaction.
Workers claim under the same row lock and accept pending_dispatch/retry_wait
as well as queued, so a fast delivery waits for the dispatcher transaction.
A crash after broker acceptance can cause a duplicate message; fencing makes
those duplicate deliveries harmless.
"""
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.upload_processing_job import UploadProcessingJob


def dispatch_upload_processing_jobs(
    db: Session,
    *,
    publish: Callable[[str], object],
    batch_size: int = 25,
    redeliver_after_seconds: int = 60,
) -> list[str]:
    """Publish a bounded batch; caller owns commit/rollback.

    Publishing occurs while holding each row lock. This deliberately keeps
    the publish/queued transition ordered relative to worker claims. The
    broker call must have a bounded timeout. A failed publish raises and
    leaves the current row unchanged; callers should roll back the batch.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    if redeliver_after_seconds <= 0:
        raise ValueError("redeliver_after_seconds must be positive")

    now = datetime.now(timezone.utc)
    redeliver_before = now - timedelta(seconds=redeliver_after_seconds)
    due = or_(
        UploadProcessingJob.status.in_({"pending_dispatch", "retry_wait"}),
        (
            (UploadProcessingJob.status == "queued")
            & (UploadProcessingJob.updated_at <= redeliver_before)
        ),
    )
    jobs = db.execute(
        select(UploadProcessingJob)
        .where(
            due,
            UploadProcessingJob.available_at <= now,
        )
        .order_by(
            UploadProcessingJob.available_at.asc(),
            UploadProcessingJob.created_at.asc(),
            UploadProcessingJob.id.asc(),
        )
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    ).scalars().all()

    dispatched: list[str] = []
    for job in jobs:
        publish(job.id)
        job.status = "queued"
        job.updated_at = now
        dispatched.append(job.id)
    db.flush()
    return dispatched
