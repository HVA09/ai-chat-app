"Tests for the isolated durable upload extraction worker."""
from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import User
from app.models.file_attachment import FileAttachment
from app.models.upload_processing_job import UploadProcessingJob
from app.services.file_text_extractor import FileTextExtractionError
from app.services.storage import PreserveMaterializedFile
from app.services.upload_leases import (
    claim_upload_lease,
    create_upload_lease,
    finalize_upload_lease,
    queue_upload_lease,
)
from app.services.upload_processing_jobs import create_upload_processing_job
from app.services.upload_processing_worker import (
    UploadProcessingWorkerError,
    process_upload_extraction_job,
)


def _committed_attachment(client, db_session, email):
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass123"},
    )
    assert response.status_code in (200, 201), response.text
    user = db_session.query(User).filter(User.email == email).one()
    object_key = f"users/{user.id}/{email}.txt"
    lease, ingress_token = create_upload_lease(
        db_session, user_id=user.id, object_key=object_key
    )
    assert queue_upload_lease(
        db_session, lease_id=lease.id, generation=1, owner_token=ingress_token
    )
    processing_claim = claim_upload_lease(
        db_session, lease_id=lease.id, lease_seconds=300
    )
    assert processing_claim is not None
    lease_generation, lease_token = processing_claim

    attachment = FileAttachment(
        user_id=user.id,
        original_filename="worker.txt",
        stored_filename=f"{email}.txt",
        object_key=object_key,
        content_type="text/plain",
        size_bytes=12,
        extracted_text=None,
    )
    db_session.add(attachment)
    db_session.flush()
    assert finalize_upload_lease(
        db_session,
        lease_id=lease.id,
        generation=lease_generation,
        owner_token=lease_token,
        attachment_id=attachment.id,
    )
    job, created = create_upload_processing_job(
        db_session, lease_id=lease.id, stage="extract"
    )
    assert created
    db_session.commit()
    return user, lease, attachment, job


def _fake_materialize(*_args, **_kwargs):
    @contextmanager
    def materialized():
        yield Path("/tmp/worker-test-source.txt")
    return materialized()


def test_extraction_worker_persists_result_and_enqueues_index_job(
    client, db_session, monkeypatch
):
    from app.services import upload_processing_worker as worker

    user, lease, attachment, job = _committed_attachment(
        client, db_session, "worker-success@example.com"
    )
    monkeypatch.setattr(worker, "materialize_file", _fake_materialize)
    monkeypatch.setattr(worker, "extract_text", lambda *_args: "  extracted text  ")

    assert process_upload_extraction_job(db_session, job_id=job.id) is True

    db_session.refresh(attachment)
    db_session.refresh(job)
    assert attachment.extracted_text == "  extracted text  "
    assert job.status == "succeeded"
    index_job = (
        db_session.query(UploadProcessingJob)
        .filter_by(lease_id=lease.id, stage="index", stage_revision=1)
        .one()
    )
    assert index_job.status == "pending_dispatch"
    assert index_job.attempt_count == 0
    assert user.id == attachment.user_id


def test_extraction_worker_duplicate_delivery_is_noop(
    client, db_session, monkeypatch
):
    from app.services import upload_processing_worker as worker

    _, _, attachment, job = _committed_attachment(
        client, db_session, "worker-duplicate@example.com"
    )
    attachment_id = attachment.id
    monkeypatch.setattr(worker, "materialize_file", _fake_materialize)
    monkeypatch.setattr(worker, "extract_text", lambda *_args: "extracted")

    assert process_upload_extraction_job(db_session, job_id=job.id) is True
    assert process_upload_extraction_job(db_session, job_id=job.id) is False
    # The worker deliberately commits and releases its connection around I/O;
    # assert against a fresh scalar read rather than refreshing the pre-worker
    # ORM instance retained by the test helper.
    extracted_text = db_session.execute(
        select(FileAttachment.extracted_text).where(FileAttachment.id == attachment_id)
    ).scalar_one()
    assert extracted_text == "extracted"


def test_extraction_worker_rejects_pending_caller_changes(
    client, db_session
):
    _, _, attachment, job = _committed_attachment(
        client, db_session, "worker-dirty-session@example.com"
    )
    attachment.extracted_text = "caller-owned pending value"

    with pytest.raises(UploadProcessingWorkerError, match="clean session"):
        process_upload_extraction_job(db_session, job_id=job.id)

    assert attachment.extracted_text == "caller-owned pending value"
    assert attachment in db_session.dirty


def test_extraction_worker_marks_invalid_document_terminal(
    client, db_session, monkeypatch
):
    from app.services import upload_processing_worker as worker

    _, _, attachment, job = _committed_attachment(
        client, db_session, "worker-invalid@example.com"
    )
    monkeypatch.setattr(worker, "materialize_file", _fake_materialize)

    def invalid_document(*_args):
        raise FileTextExtractionError("sensitive parser details")

    monkeypatch.setattr(worker, "extract_text", invalid_document)
    assert process_upload_extraction_job(db_session, job_id=job.id) is False

    db_session.refresh(job)
    db_session.refresh(attachment)
    assert job.status == "failed_terminal"
    assert job.last_error_code == "document_extraction_invalid"
    assert "sensitive" not in (job.last_error_code or "")
    assert attachment.extracted_text is None


def test_extraction_worker_retries_transient_storage_failure(
    client, db_session, monkeypatch
):
    from app.services import upload_processing_worker as worker

    _, _, attachment, job = _committed_attachment(
        client, db_session, "worker-storage-retry@example.com"
    )

    def storage_unavailable(*_args, **_kwargs):
        raise worker.StorageError("sensitive storage backend details")

    monkeypatch.setattr(worker, "materialize_file", storage_unavailable)

    assert process_upload_extraction_job(db_session, job_id=job.id) is False

    db_session.refresh(job)
    db_session.refresh(attachment)
    assert job.status == "retry_wait"
    assert job.attempt_count == 1
    assert job.last_error_code == "storage_read_failed"
    assert job.owner_token_hash is None
    assert job.expires_at is None
    assert attachment.extracted_text is None
    assert "sensitive" not in (job.last_error_code or "")


def test_extraction_worker_discards_result_when_fence_is_lost(
    client, db_session, monkeypatch
):
    from app.services import upload_processing_worker as worker

    _, _, attachment, job = _committed_attachment(
        client, db_session, "worker-lost-fence@example.com"
    )
    monkeypatch.setattr(worker, "materialize_file", _fake_materialize)
    monkeypatch.setattr(worker, "extract_text", lambda *_args: "must not persist")
    monkeypatch.setattr(worker, "heartbeat_upload_processing_job", lambda *_args, **_kwargs: False)

    assert process_upload_extraction_job(db_session, job_id=job.id) is False

    db_session.refresh(attachment)
    db_session.refresh(job)
    assert attachment.extracted_text is None
    assert job.status == "processing"
    assert job.owner_token_hash is not None
    assert job.completed_at is None


def test_extraction_worker_fails_closed_when_parser_cannot_confirm_stop(
    client, db_session, monkeypatch
):
    from app.services import upload_processing_worker as worker

    _, lease, attachment, job = _committed_attachment(
        client, db_session, "worker-parser-stop-unknown@example.com"
    )
    source_path = Path("/tmp/retained-parser-source.txt")
    heartbeat_calls = []

    @contextmanager
    def parser_source(*_args, **_kwargs):
        yield source_path
        raise PreserveMaterializedFile(source_path)

    def unexpected_heartbeat(*_args, **_kwargs):
        heartbeat_calls.append(True)
        return True

    monkeypatch.setattr(worker, "materialize_file", parser_source)
    monkeypatch.setattr(worker, "extract_text", lambda *_args: "must not persist")
    monkeypatch.setattr(worker, "heartbeat_upload_processing_job", unexpected_heartbeat)

    with pytest.raises(PreserveMaterializedFile):
        process_upload_extraction_job(db_session, job_id=job.id)

    db_session.expire_all()
    stored_text = db_session.execute(
        select(FileAttachment.extracted_text).where(FileAttachment.id == attachment.id)
    ).scalar_one()
    stored_job = db_session.get(UploadProcessingJob, job.id)
    stored_lease = db_session.get(type(lease), lease.id)

    assert stored_text is None
    assert stored_job.status == "processing"
    assert stored_job.owner_token_hash is not None
    assert stored_job.completed_at is None
    assert stored_lease.status == "committed"
    assert heartbeat_calls == []

def test_extraction_worker_classifies_unexpected_parser_failure(
    client, db_session, monkeypatch
):
    from app.services import upload_processing_worker as worker

    _, _, attachment, job = _committed_attachment(
        client, db_session, "worker-unexpected-error@example.com"
    )
    monkeypatch.setattr(worker, "materialize_file", _fake_materialize)

    def unexpected_parser_failure(*_args):
        raise RuntimeError("private parser path and document details")

    monkeypatch.setattr(worker, "extract_text", unexpected_parser_failure)

    assert process_upload_extraction_job(db_session, job_id=job.id) is False

    db_session.refresh(job)
    db_session.refresh(attachment)
    assert job.status == "failed_terminal"
    assert job.last_error_code == "extraction_internal_error"
    assert "private" not in (job.last_error_code or "")
    assert attachment.extracted_text is None
