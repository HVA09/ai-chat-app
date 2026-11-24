"""Tests for the isolated durable upload extraction worker."""
from contextlib import contextmanager

from app.models import User
from app.models.file_attachment import FileAttachment
from app.models.upload_processing_job import UploadProcessingJob
from app.services.file_text_extractor import FileTextExtractionError
from app.services.upload_leases import (
    claim_upload_lease,
    create_upload_lease,
    finalize_upload_lease,
    queue_upload_lease,
)
from app.services.upload_processing_jobs import create_upload_processing_job
from app.services.upload_processing_worker import process_upload_extraction_job


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
        yield __import__("pathlib").Path("/tmp/worker-test-source.txt")
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
    monkeypatch.setattr(worker, "materialize_file", _fake_materialize)
    monkeypatch.setattr(worker, "extract_text", lambda *_args: "extracted")

    assert process_upload_extraction_job(db_session, job_id=job.id) is True
    assert process_upload_extraction_job(db_session, job_id=job.id) is False
    db_session.refresh(attachment)
    assert attachment.extracted_text == "extracted"


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
