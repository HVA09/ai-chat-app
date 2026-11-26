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
    db_session.commit()

    def fail_publish(_job_id):
        raise RuntimeError("broker unavailable")

    with pytest.raises(RuntimeError, match="broker unavailable"):
        dispatch_upload_processing_jobs(db_session, publish=fail_publish)

    # A failed publish occurs before the dispatcher mutates/flushed the row.
    # Avoid rolling back the test fixture savepoint, which would discard setup data.
    db_session.refresh(job)
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



def test_concurrent_dispatchers_skip_rows_locked_by_another_dispatcher(db_session):
    """A second dispatcher must skip a row while its publish is in flight."""
    import os
    from threading import Event, Thread
    from uuid import uuid4

    from sqlalchemy.orm import sessionmaker
    from app.models.upload_lease import UploadLease

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    if engine.dialect.name != "postgresql":
        pytest.skip("dispatcher row-lock behavior requires PostgreSQL")
    if "test" not in (engine.url.database or "").lower():
        pytest.skip("database name is not clearly marked as a test database")
    if os.getenv("ENVIRONMENT", "test").lower() != "test":
        pytest.skip("test environment guard is not active")

    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    suffix = uuid4().hex
    user_id = lease_id = job_id = None
    publish_entered = Event()
    allow_publish_to_finish = Event()
    first_results = []
    errors = []

    try:
        with factory() as setup:
            user = User(
                email=f"pg-concurrent-dispatch-{suffix}@example.test",
                hashed_password="test-only",
            )
            setup.add(user)
            setup.flush()
            user_id = user.id
            lease, token = create_upload_lease(
                setup,
                user_id=user.id,
                object_key=f"users/{user.id}/{suffix}.bin",
            )
            lease_id = lease.id
            assert queue_upload_lease(
                setup, lease_id=lease.id, generation=1, owner_token=token
            )
            job, created = create_upload_processing_job(
                setup, lease_id=lease.id, stage="extract"
            )
            assert created
            job_id = job.id
            setup.commit()

        def first_dispatcher():
            try:
                with factory() as session:
                    def blocking_publish(published_job_id):
                        assert published_job_id == job_id
                        publish_entered.set()
                        assert allow_publish_to_finish.wait(timeout=10), (
                            "test did not release the in-flight publish"
                        )

                    first_results.extend(
                        dispatch_upload_processing_jobs(
                            session, publish=blocking_publish
                        )
                    )
                    session.commit()
            except BaseException as exc:
                errors.append(exc)
                publish_entered.set()

        thread = Thread(target=first_dispatcher)
        thread.start()
        assert publish_entered.wait(timeout=10), "first dispatcher did not begin publish"

        # The first dispatcher is paused inside publish while retaining its
        # FOR UPDATE lock. SKIP LOCKED must let the second dispatcher return
        # promptly without publishing or waiting for that same row.
        with factory() as second:
            second_published = []
            second_results = dispatch_upload_processing_jobs(
                second, publish=lambda value: second_published.append(value)
            )
            second.commit()

        assert second_results == []
        assert second_published == []
        allow_publish_to_finish.set()
        thread.join(timeout=15)
        assert not thread.is_alive(), "first dispatcher hung"
        assert errors == []
        assert first_results == [job_id]

        with factory() as verify:
            persisted = verify.get(UploadProcessingJob, job_id)
            assert persisted is not None
            assert persisted.status == "queued"
    finally:
        allow_publish_to_finish.set()
        if user_id is not None:
            with factory() as cleanup:
                if job_id is not None:
                    cleanup.query(UploadProcessingJob).filter_by(id=job_id).delete()
                if lease_id is not None:
                    cleanup.query(UploadLease).filter_by(id=lease_id).delete()
                cleanup.query(User).filter_by(id=user_id).delete()
                cleanup.commit()
