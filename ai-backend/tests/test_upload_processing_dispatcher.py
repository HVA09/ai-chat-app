"""Tests for the durable upload-processing outbox dispatcher."""
from datetime import datetime, timedelta, timezone

import pytest

from app.models import User
from app.models.upload_processing_job import UploadProcessingJob
from app.services.upload_leases import create_upload_lease, queue_upload_lease
from app.services.upload_processing_dispatcher import dispatch_upload_processing_jobs
from app.services.upload_processing_jobs import (
    claim_upload_processing_job,
    create_upload_processing_job,
)


def _make_job(client, db_session, email, stage="extract"):
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass123"},
    )
    assert response.status_code in (200, 201), response.text
    user = db_session.query(User).filter(User.email == email).one()
    lease, token = create_upload_lease(
        db_session,
        user_id=user.id,
        object_key=f"users/{user.id}/{email}.bin",
    )
    assert queue_upload_lease(
        db_session, lease_id=lease.id, generation=1, owner_token=token
    )
    job, created = create_upload_processing_job(
        db_session, lease_id=lease.id, stage=stage
    )
    assert created
    db_session.flush()
    return job


def test_dispatch_marks_job_queued_and_worker_can_claim(client, db_session):
    job = _make_job(client, db_session, "upload-dispatch-success@example.com")
    published = []

    dispatched = dispatch_upload_processing_jobs(
        db_session, publish=lambda job_id: published.append(job_id)
    )

    assert dispatched == [job.id]
    assert published == [job.id]
    db_session.commit()
    db_session.refresh(job)
    assert job.status == "queued"

    # A fresh queued row is not repeatedly published on every dispatcher tick.
    assert dispatch_upload_processing_jobs(
        db_session, publish=lambda job_id: pytest.fail("unexpected duplicate")
    ) == []

    claim = claim_upload_processing_job(db_session, job_id=job.id)
    assert claim is not None
    db_session.refresh(job)
    assert job.status == "processing"


def test_dispatch_publish_failure_leaves_job_retryable(client, db_session):
    job = _make_job(client, db_session, "upload-dispatch-failure@example.com")
    job_id = job.id
    db_session.commit()

    def fail_publish(_job_id):
        raise RuntimeError("broker unavailable")

    with pytest.raises(RuntimeError, match="broker unavailable"):
        dispatch_upload_processing_jobs(db_session, publish=fail_publish)

    db_session.rollback()
    job = db_session.query(UploadProcessingJob).filter(UploadProcessingJob.id == job_id).one()
    assert job.status == "pending_dispatch"
    assert job.generation == 0
    assert job.attempt_count == 0


def test_dispatch_redelivers_stale_queued_message(client, db_session):
    job = _make_job(client, db_session, "upload-dispatch-redelivery@example.com")
    published = []
    assert dispatch_upload_processing_jobs(
        db_session, publish=lambda job_id: published.append(job_id)
    ) == [job.id]
    db_session.commit()

    job.updated_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()

    redelivered = dispatch_upload_processing_jobs(
        db_session, publish=lambda job_id: published.append(job_id),
        redeliver_after_seconds=60,
    )
    assert redelivered == [job.id]
    assert published == [job.id, job.id]
    db_session.commit()
    db_session.refresh(job)
    assert job.status == "queued"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"batch_size": 0},
        {"batch_size": -1},
        {"redeliver_after_seconds": 0},
    ],
)
def test_dispatch_rejects_invalid_bounds(db_session, kwargs):
    with pytest.raises(ValueError):
        dispatch_upload_processing_jobs(db_session, publish=lambda _job_id: None, **kwargs)
