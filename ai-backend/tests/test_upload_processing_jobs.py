"""Unit/integration coverage for durable upload-processing job transitions."""
import pytest

from app.models import User, UploadLease
from app.models.upload_processing_job import UploadProcessingJob
from app.services.upload_leases import create_upload_lease, queue_upload_lease
from app.services.upload_processing_jobs import (
    claim_upload_processing_job,
    complete_upload_processing_job,
    create_upload_processing_job,
    fail_upload_processing_job,
    heartbeat_upload_processing_job,
    queue_upload_processing_job,
    retry_upload_processing_job,
)


def _user(client, db_session, email):
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass123"},
    )
    assert response.status_code in (200, 201), response.text
    return db_session.query(User).filter(User.email == email).one()


def _queued_lease(db_session, user):
    lease, token = create_upload_lease(
        db_session,
        user_id=user.id,
        object_key=f"users/{user.id}/processing-job-{user.email}.bin",
    )
    assert queue_upload_lease(
        db_session, lease_id=lease.id, generation=1, owner_token=token
    )
    return lease


def test_processing_job_creation_is_idempotent(client, db_session):
    user = _user(client, db_session, "upload-job-idempotent@example.com")
    lease = _queued_lease(db_session, user)

    first, created = create_upload_processing_job(
        db_session, lease_id=lease.id, stage="extract"
    )
    second, created_again = create_upload_processing_job(
        db_session, lease_id=lease.id, stage="extract"
    )

    assert created is True
    assert created_again is False
    assert first.id == second.id
    assert db_session.query(UploadProcessingJob).filter_by(lease_id=lease.id).count() == 1


def test_processing_job_claim_fencing_and_completion(client, db_session):
    user = _user(client, db_session, "upload-job-claim@example.com")
    lease = _queued_lease(db_session, user)
    job, created = create_upload_processing_job(
        db_session, lease_id=lease.id, stage="extract"
    )
    assert created
    assert queue_upload_processing_job(db_session, job_id=job.id)

    claim = claim_upload_processing_job(db_session, job_id=job.id, lease_seconds=60)
    assert claim is not None
    generation, token = claim
    assert generation == 1
    assert claim_upload_processing_job(db_session, job_id=job.id) is None
    assert not heartbeat_upload_processing_job(
        db_session, job_id=job.id, generation=generation - 1,
        owner_token=token, lease_seconds=60,
    )
    assert heartbeat_upload_processing_job(
        db_session, job_id=job.id, generation=generation,
        owner_token=token, lease_seconds=60,
    )
    assert not complete_upload_processing_job(
        db_session, job_id=job.id, generation=generation,
        owner_token="stale-token",
    )
    assert complete_upload_processing_job(
        db_session, job_id=job.id, generation=generation, owner_token=token
    )
    assert not complete_upload_processing_job(
        db_session, job_id=job.id, generation=generation, owner_token=token
    )
    db_session.refresh(job)
    assert job.status == "succeeded"
    assert job.owner_token_hash is None


def test_processing_job_retry_and_terminal_failure(client, db_session):
    user = _user(client, db_session, "upload-job-retry@example.com")
    lease = _queued_lease(db_session, user)
    job, _ = create_upload_processing_job(
        db_session, lease_id=lease.id, stage="index", max_attempts=2
    )
    assert queue_upload_processing_job(db_session, job_id=job.id)
    generation, token = claim_upload_processing_job(db_session, job_id=job.id)
    assert retry_upload_processing_job(
        db_session, job_id=job.id, generation=generation, owner_token=token,
        error_code="provider_timeout", delay_seconds=0,
    )
    db_session.refresh(job)
    assert job.status == "retry_wait"
    assert queue_upload_processing_job(db_session, job_id=job.id)
    generation, token = claim_upload_processing_job(db_session, job_id=job.id)
    assert fail_upload_processing_job(
        db_session, job_id=job.id, generation=generation, owner_token=token,
        error_code="unsupported_format",
    )
    db_session.refresh(job)
    assert job.status == "failed_terminal"
    assert job.last_error_code == "unsupported_format"


@pytest.mark.parametrize("stage", ["bad", "", "EXTRACT"])
def test_processing_job_rejects_unknown_stage(db_session, stage):
    with pytest.raises(ValueError, match="stage must be"):
        create_upload_processing_job(
            db_session, lease_id="missing", stage=stage
        )


def test_expired_processing_job_is_not_reclaimed(client, db_session):
    user = _user(client, db_session, "upload-job-expiry@example.com")
    lease = _queued_lease(db_session, user)
    job, _ = create_upload_processing_job(
        db_session, lease_id=lease.id, stage="extract"
    )
    assert queue_upload_processing_job(db_session, job_id=job.id)
    generation, token = claim_upload_processing_job(
        db_session, job_id=job.id, lease_seconds=1
    )
    # Expiry is advisory only: claim requires status='queued', not a timestamp.
    job.expires_at = job.created_at
    db_session.flush()
    assert claim_upload_processing_job(db_session, job_id=job.id) is None
    db_session.refresh(job)
    assert job.status == "processing"
    assert job.generation == generation
    assert job.owner_token_hash is not None
