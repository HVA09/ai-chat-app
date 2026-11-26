"""Durable upload extraction worker logic (not process-isolated).

This module is intentionally not wired to an API route, scheduler, broker
consumer, or application startup. Parsing still runs in-process; the standalone
parser supervisor is not integrated. A later cutover must first close the
isolation and failure-matrix gates, then create the job atomically with
attachment finalization before invoking this worker.
"""
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import commit_and_release_connection
from app.models.file_attachment import FileAttachment
from app.models.upload_lease import UploadLease
from app.models.upload_processing_job import UploadProcessingJob
from app.services.file_text_extractor import FileTextExtractionError, extract_text
from app.services.storage import StorageError, materialize_file
from app.services.upload_processing_jobs import (
    claim_upload_processing_job,
    complete_upload_processing_job,
    create_upload_processing_job,
    fail_upload_processing_job,
    heartbeat_upload_processing_job,
    retry_upload_processing_job,
)

PROCESSING_LEASE_SECONDS = 300
STORAGE_RETRY_DELAY_SECONDS = 30


class UploadProcessingWorkerError(RuntimeError):
    """A safe, non-sensitive worker failure."""


def process_upload_extraction_job(db: Session, *, job_id: str) -> bool:
    """Claim and execute one extraction job; return False for duplicate delivery.

    This function owns its Session transaction boundaries: it commits the
    durable claim before external I/O and commits the final result atomically.
    Callers must supply a clean, dedicated Session with no pending ORM writes;
    this prevents worker commits/rollbacks from affecting unrelated work.
    No storage deletion or lease reclamation is performed here.
    """
    if db.new or db.dirty or db.deleted:
        raise UploadProcessingWorkerError(
            "worker requires a clean session with no pending ORM changes"
        )

    locator = db.execute(
        select(UploadProcessingJob.stage).where(UploadProcessingJob.id == job_id)
    ).scalar_one_or_none()
    if locator != "extract":
        db.rollback()
        return False

    claim = claim_upload_processing_job(
        db, job_id=job_id, lease_seconds=PROCESSING_LEASE_SECONDS
    )
    if claim is None:
        # A failed claim is either a duplicate/no-op or a max-attempts
        # transition to failed_terminal. The clean-session precondition makes
        # this commit safe: there can be no unrelated pending ORM writes.
        db.commit()
        return False
    generation, owner_token = claim
    db.commit()

    snapshot = db.execute(
        select(UploadLease, FileAttachment)
        .join(FileAttachment, FileAttachment.id == UploadLease.attachment_id)
        .where(
            UploadLease.id == select(UploadProcessingJob.lease_id)
            .where(UploadProcessingJob.id == job_id)
            .scalar_subquery(),
            UploadLease.status == "committed",
        )
    ).one_or_none()
    if snapshot is None:
        db.rollback()
        if fail_upload_processing_job(
            db, job_id=job_id, generation=generation,
            owner_token=owner_token, error_code="attachment_missing",
        ):
            db.commit()
        else:
            db.rollback()
        return False

    lease, attachment = snapshot
    user_id = lease.user_id
    if user_id is None or attachment.user_id != user_id:
        db.rollback()
        if fail_upload_processing_job(
            db, job_id=job_id, generation=generation,
            owner_token=owner_token, error_code="attachment_owner_mismatch",
        ):
            db.commit()
        else:
            db.rollback()
        return False

    fallback_path = (
        Path(settings.UPLOAD_DIR) / str(user_id) / attachment.stored_filename
    )
    object_key = lease.object_key
    content_type = attachment.content_type

    # Release the DB checkout before materializing remote storage or parsing.
    commit_and_release_connection(db)
    try:
        with materialize_file(object_key, fallback_path) as local_path:
            extracted = extract_text(local_path, content_type)
    except StorageError:
        db.rollback()
        if retry_upload_processing_job(
            db, job_id=job_id, generation=generation, owner_token=owner_token,
            error_code="storage_read_failed", delay_seconds=STORAGE_RETRY_DELAY_SECONDS,
        ):
            db.commit()
        else:
            db.rollback()
        return False
    except FileNotFoundError:
        db.rollback()
        if fail_upload_processing_job(
            db, job_id=job_id, generation=generation,
            owner_token=owner_token, error_code="source_file_missing",
        ):
            db.commit()
        else:
            db.rollback()
        return False
    except FileTextExtractionError:
        db.rollback()
        if fail_upload_processing_job(
            db, job_id=job_id, generation=generation,
            owner_token=owner_token, error_code="document_extraction_invalid",
        ):
            db.commit()
        else:
            db.rollback()
        return False
    except PreserveMaterializedFile:
        # The parser may still own/read the materialized source. Preserve the
        # durable processing claim and let the explicit recovery protocol decide.
        db.rollback()
        raise
    except Exception:
        # Do not strand a job in processing for an unclassified local failure.
        # Keep the source and record only a bounded, non-sensitive error code.
        db.rollback()
        if fail_upload_processing_job(
            db, job_id=job_id, generation=generation,
            owner_token=owner_token, error_code="extraction_internal_error",
        ):
            db.commit()
        else:
            db.rollback()
        return False

    # Revalidate the worker fence before any result write. The helper acquires
    # User -> Lease -> Job locks; the attachment row is then locked in that
    # transaction and checked against the committed lease snapshot.
    if not heartbeat_upload_processing_job(
        db, job_id=job_id, generation=generation,
        owner_token=owner_token, lease_seconds=PROCESSING_LEASE_SECONDS,
    ):
        db.rollback()
        return False

    current = db.execute(
        select(FileAttachment)
        .where(
            FileAttachment.id == attachment.id,
            FileAttachment.user_id == user_id,
            FileAttachment.object_key == attachment.object_key,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    current_lease = db.execute(
        select(UploadLease).where(
            UploadLease.id == lease.id,
            UploadLease.user_id == user_id,
            UploadLease.status == "committed",
            UploadLease.attachment_id == attachment.id,
            UploadLease.object_key == object_key,
        )
    ).scalar_one_or_none()
    if current is None or current_lease is None:
        db.rollback()
        return False

    current.extracted_text = extracted
    if not complete_upload_processing_job(
        db, job_id=job_id, generation=generation, owner_token=owner_token
    ):
        db.rollback()
        return False

    if extracted and extracted.strip():
        create_upload_processing_job(
            db, lease_id=lease.id, stage="index", stage_revision=1
        )
    db.commit()
    return True
