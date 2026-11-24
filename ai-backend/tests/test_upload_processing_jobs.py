"""Unit/integration coverage for durable upload-processing job transitions."""
import pytest

from app.models import User
from app.models.upload_processing_job import UploadProcessingJob
from app.services.upload_leases import create_upload_lease, queue_upload_lease
from app.services.upload_processing_jobs import (
    claim_upload_processing_job,
    complete_upload_processing_job,
    create_upload_processing_job,
    fail_upload_processing_job,
    heartbeat_upload_processing_job,
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
    generation, token = claim_upload_processing_job(db_session, job_id=job.id)
    assert retry_upload_processing_job(
        db_session, job_id=job.id, generation=generation, owner_token=token,
        error_code="provider_timeout", delay_seconds=0,
    )
    db_session.refresh(job)
    assert job.status == "retry_wait"
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
    generation, _ = claim_upload_processing_job(
        db_session, job_id=job.id, lease_seconds=1
    )
    # Expiry is advisory only: claim requires an undispatched outbox state, not a timestamp.
    job.expires_at = job.created_at
    db_session.flush()
    assert claim_upload_processing_job(db_session, job_id=job.id) is None
    db_session.refresh(job)
    assert job.status == "processing"
    assert job.generation == generation
    assert job.owner_token_hash is not None



def test_processing_job_claim_is_single_winner_across_independent_postgres_sessions(
    db_session,
):
    """Concurrent claims on committed data from independent PostgreSQL sessions."""
    import os
    from threading import Barrier, Thread
    from uuid import uuid4

    from sqlalchemy.orm import sessionmaker

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    if engine.dialect.name != "postgresql":
        pytest.skip("independent-session locking behavior requires PostgreSQL")

    # Fail closed if the test URL points at a database whose name does not
    # clearly identify it as a test database. Never run this against production.
    database_name = engine.url.database or ""
    if "test" not in database_name.lower():
        pytest.skip("database name is not clearly marked as a test database")
    if os.getenv("ENVIRONMENT", "test").lower() != "test":
        pytest.skip("test environment guard is not active")

    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    suffix = uuid4().hex
    user_id = None
    lease_id = None
    job_id = None
    try:
        with factory() as setup:
            user = User(
                email=f"pg-concurrent-claim-{suffix}@example.test",
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
            job, _ = create_upload_processing_job(
                setup, lease_id=lease.id, stage="extract"
            )
            job_id = job.id
            setup.commit()

        barrier = Barrier(2)
        results = []
        errors = []

        def claimant():
            try:
                with factory() as session:
                    barrier.wait(timeout=10)
                    results.append(
                        claim_upload_processing_job(session, job_id=job_id)
                    )
                    session.commit()
            except BaseException as exc:
                errors.append(exc)

        threads = [Thread(target=claimant), Thread(target=claimant)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        assert all(not thread.is_alive() for thread in threads), "claim thread hung"
        assert errors == []
        assert len(results) == 2
        assert sum(result is not None for result in results) == 1, results

        with factory() as verify:
            persisted = verify.get(UploadProcessingJob, job_id)
            assert persisted is not None
            assert persisted.status == "processing"
            assert persisted.generation == 1
            assert persisted.attempt_count == 1
            assert persisted.owner_token_hash is not None
    finally:
        # Cleanup only the committed test records created by this test.
        if user_id is not None:
            with factory() as cleanup:
                if job_id is not None:
                    cleanup.query(UploadProcessingJob).filter_by(id=job_id).delete()
                if lease_id is not None:
                    from app.models.upload_lease import UploadLease
                    cleanup.query(UploadLease).filter_by(id=lease_id).delete()
                cleanup.query(User).filter_by(id=user_id).delete()
                cleanup.commit()


def test_processing_job_creation_is_single_row_across_independent_postgres_sessions(
    db_session,
):
    """Concurrent idempotent outbox creation yields one durable row."""
    import os
    from threading import Barrier, Thread
    from uuid import uuid4

    from sqlalchemy.orm import sessionmaker

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    if engine.dialect.name != "postgresql":
        pytest.skip("independent-session locking behavior requires PostgreSQL")
    database_name = engine.url.database or ""
    if "test" not in database_name.lower():
        pytest.skip("database name is not clearly marked as a test database")
    if os.getenv("ENVIRONMENT", "test").lower() != "test":
        pytest.skip("test environment guard is not active")

    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    suffix = uuid4().hex
    user_id = lease_id = None
    results, errors = [], []
    try:
        with factory() as setup:
            user = User(email=f"pg-concurrent-create-{suffix}@example.test",
                        hashed_password="test-only")
            setup.add(user)
            setup.flush()
            user_id = user.id
            lease, token = create_upload_lease(
                setup, user_id=user.id,
                object_key=f"users/{user.id}/{suffix}.bin",
            )
            lease_id = lease.id
            assert queue_upload_lease(
                setup, lease_id=lease.id, generation=1, owner_token=token
            )
            setup.commit()

        barrier = Barrier(2)

        def creator():
            try:
                with factory() as session:
                    barrier.wait(timeout=10)
                    job, created = create_upload_processing_job(
                        session, lease_id=lease_id, stage="extract"
                    )
                    results.append((job.id, created))
                    session.commit()
            except BaseException as exc:
                errors.append(exc)

        threads = [Thread(target=creator), Thread(target=creator)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        assert all(not thread.is_alive() for thread in threads), "creation thread hung"
        assert errors == []
        assert len(results) == 2
        assert results[0][0] == results[1][0]
        assert sum(created for _, created in results) == 1

        with factory() as verify:
            rows = verify.query(UploadProcessingJob).filter_by(
                lease_id=lease_id, stage="extract", stage_revision=1
            ).all()
            assert len(rows) == 1
            assert rows[0].status == "pending_dispatch"
            assert rows[0].generation == 0
            assert rows[0].attempt_count == 0
    finally:
        if user_id is not None:
            with factory() as cleanup:
                if lease_id is not None:
                    cleanup.query(UploadProcessingJob).filter_by(
                        lease_id=lease_id
                    ).delete()
                    from app.models.upload_lease import UploadLease
                    cleanup.query(UploadLease).filter_by(id=lease_id).delete()
                cleanup.query(User).filter_by(id=user_id).delete()
                cleanup.commit()


def test_account_deletion_serializes_with_concurrent_job_claim(client, db_session):
    """A claim waiting behind account deletion must fail closed after deletion commits."""
    import os
    from threading import Event, Thread
    from uuid import uuid4

    from sqlalchemy import select
    from sqlalchemy.orm import sessionmaker
    from app.models.upload_lease import UploadLease

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    if engine.dialect.name != "postgresql":
        pytest.skip("account-deletion row-lock serialization requires PostgreSQL")
    if "test" not in (engine.url.database or "").lower():
        pytest.skip("database name is not clearly marked as a test database")
    if os.getenv("ENVIRONMENT", "test").lower() != "test":
        pytest.skip("test environment guard is not active")

    email = f"upload-delete-race-{uuid4().hex}@example.com"
    user = _user(client, db_session, email)
    user_id = user.id
    lease = _queued_lease(db_session, user)
    job, _ = create_upload_processing_job(
        db_session, lease_id=lease.id, stage="extract"
    )
    lease_id, job_id = lease.id, job.id
    db_session.commit()

    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    deletion_locked = Event()
    allow_deletion_commit = Event()
    claim_started = Event()
    claim_finished = Event()
    claim_results, errors = [], []

    def delete_account_row():
        import traceback

        try:
            with factory() as deleting:
                locked_user = deleting.execute(
                    select(User).where(User.id == user_id).with_for_update()
                ).scalar_one()
                deletion_locked.set()
                assert allow_deletion_commit.wait(timeout=10)
                deleting.delete(locked_user)
                deleting.commit()
        except BaseException as exc:
            errors.append((exc, traceback.format_exc()))
            deletion_locked.set()

    def claim_job():
        import traceback

        try:
            with factory() as claiming:
                claim_started.set()
                claim_results.append(
                    claim_upload_processing_job(claiming, job_id=job_id)
                )
                claiming.commit()
        except BaseException as exc:
            errors.append((exc, traceback.format_exc()))
        finally:
            claim_finished.set()

    deleter = Thread(target=delete_account_row)
    claimant = Thread(target=claim_job)
    try:
        deleter.start()
        assert deletion_locked.wait(timeout=10), "deletion did not acquire user lock"
        claimant.start()
        assert claim_started.wait(timeout=10), "claim thread did not start"
        # If the worker exits early, surface its exception/result before
        # reporting a lock-order failure; this distinguishes infrastructure
        # errors from a genuine lock bypass.
        if claim_finished.wait(timeout=0.25):
            assert errors == [], f"claim thread failed before lock assertion: {errors!r}"
            pytest.fail(
                "claim completed before deletion committed; "
                f"claim_results={claim_results!r}"
            )
        allow_deletion_commit.set()
        deleter.join(timeout=15)
        claimant.join(timeout=15)

        assert not deleter.is_alive(), "deletion thread hung"
        assert not claimant.is_alive(), "claim thread hung"
        assert errors == []
        assert claim_results == [None]

        with factory() as verify:
            persisted_lease = verify.get(UploadLease, lease_id)
            persisted_job = verify.get(UploadProcessingJob, job_id)
            assert verify.get(User, user_id) is None
            assert persisted_lease is not None
            assert persisted_lease.user_id is None
            assert persisted_job is not None
            assert persisted_job.status == "pending_dispatch"
            assert persisted_job.generation == 0
            assert persisted_job.attempt_count == 0
    finally:
        allow_deletion_commit.set()
        if deleter.is_alive():
            deleter.join(timeout=15)
        if claimant.is_alive():
            claimant.join(timeout=15)
        with factory() as cleanup:
            cleanup.query(UploadProcessingJob).filter_by(id=job_id).delete()
            cleanup.query(UploadLease).filter_by(id=lease_id).delete()
            cleanup.commit()
