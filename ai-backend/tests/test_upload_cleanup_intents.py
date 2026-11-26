from uuid import uuid4

from app.models.file_attachment import FileAttachment
from app.models.upload_cleanup_intent import UploadCleanupIntent
from app.models.user import User
from app.models.upload_lease import UploadLease
from app.services.upload_leases import (
    claim_upload_lease,
    create_upload_lease,
    mark_upload_lease_cleanup_pending,
    queue_upload_lease,
)
from app.services.upload_cleanup_intents import (
    enqueue_upload_cleanup_intent,
    record_upload_cleanup_attempt,
)


def _make_user(db_session):
    user = User(
        email=f"cleanup-intent-{uuid4().hex}@example.test",
        hashed_password="test-only-hash",
    )
    db_session.add(user)
    db_session.flush()
    return user


def test_upload_cleanup_intent_is_durable_and_idempotent(db_session):
    user = _make_user(db_session)
    object_key = f"users/{user.id}/{uuid4().hex}.txt"

    first = enqueue_upload_cleanup_intent(
        db_session, user_id=user.id, object_key=object_key
    )
    assert first is not None
    first_id = first.id
    db_session.commit()

    second = enqueue_upload_cleanup_intent(
        db_session, user_id=user.id, object_key=object_key
    )
    assert second is not None
    assert second.id == first_id
    assert second.status == "pending"
    db_session.commit()

    stored = (
        db_session.query(UploadCleanupIntent)
        .filter(UploadCleanupIntent.id == first_id)
        .one()
    )
    assert stored.object_key == object_key
    assert stored.attempt_count == 0


def test_committed_attachment_blocks_upload_cleanup_intent(db_session):
    user = _make_user(db_session)
    object_key = f"users/{user.id}/{uuid4().hex}.txt"
    attachment = FileAttachment(
        user_id=user.id,
        original_filename="committed.txt",
        stored_filename=f"{uuid4().hex}.txt",
        object_key=object_key,
        content_type="text/plain",
        size_bytes=1,
    )
    db_session.add(attachment)
    db_session.flush()

    intent = enqueue_upload_cleanup_intent(
        db_session, user_id=user.id, object_key=object_key
    )
    assert intent is None
    assert (
        db_session.query(UploadCleanupIntent)
        .filter(UploadCleanupIntent.object_key == object_key)
        .count()
        == 0
    )


def test_upload_cleanup_attempts_are_monotonic_and_completion_is_terminal(db_session):
    user = _make_user(db_session)
    object_key = f"users/{user.id}/{uuid4().hex}.txt"
    intent = enqueue_upload_cleanup_intent(
        db_session, user_id=user.id, object_key=object_key
    )
    db_session.commit()

    assert record_upload_cleanup_attempt(
        db_session,
        intent_id=intent.id,
        succeeded=False,
        error_code="storage_delete_failed",
    )
    db_session.commit()
    db_session.refresh(intent)
    assert intent.status == "pending"
    assert intent.attempt_count == 1
    assert intent.last_error_code == "storage_delete_failed"

    assert record_upload_cleanup_attempt(
        db_session,
        intent_id=intent.id,
        succeeded=True,
    )
    db_session.commit()
    db_session.refresh(intent)
    assert intent.status == "completed"
    assert intent.attempt_count == 2
    assert intent.completed_at is not None
    assert not record_upload_cleanup_attempt(
        db_session,
        intent_id=intent.id,
        succeeded=False,
        error_code="late_failure",
    )


def test_stale_processing_generation_cannot_enqueue_cleanup_intent(db_session):
    user = _make_user(db_session)
    object_key = f"users/{user.id}/{uuid4().hex}.txt"
    lease, ingress_token = create_upload_lease(
        db_session,
        user_id=user.id,
        object_key=object_key,
    )
    assert queue_upload_lease(
        db_session,
        lease_id=lease.id,
        generation=1,
        owner_token=ingress_token,
    )
    generation, worker_token = claim_upload_lease(
        db_session,
        lease_id=lease.id,
        lease_seconds=90,
    )

    # Model a later, authoritative generation taking ownership. The previous
    # worker still has its old generation/token but no longer owns the lease.
    persisted_lease = db_session.get(UploadLease, lease.id)
    persisted_lease.generation = generation + 1
    persisted_lease.status = "processing"
    persisted_lease.owner_token_hash = "f" * 64
    db_session.flush()

    assert not mark_upload_lease_cleanup_pending(
        db_session,
        lease_id=lease.id,
        generation=generation,
        owner_token=worker_token,
    )

    stale_intent = enqueue_upload_cleanup_intent(
        db_session,
        user_id=user.id,
        object_key=object_key,
        lease_id=lease.id,
        generation=generation,
    )
    assert stale_intent is None
    assert (
        db_session.query(UploadCleanupIntent)
        .filter(UploadCleanupIntent.object_key == object_key)
        .count()
        == 0
    )


def test_current_cleanup_pending_generation_can_enqueue_intent(db_session):
    user = _make_user(db_session)
    object_key = f"users/{user.id}/{uuid4().hex}.txt"
    lease, ingress_token = create_upload_lease(
        db_session,
        user_id=user.id,
        object_key=object_key,
    )
    assert queue_upload_lease(
        db_session,
        lease_id=lease.id,
        generation=1,
        owner_token=ingress_token,
    )
    generation, worker_token = claim_upload_lease(
        db_session,
        lease_id=lease.id,
        lease_seconds=90,
    )
    assert mark_upload_lease_cleanup_pending(
        db_session,
        lease_id=lease.id,
        generation=generation,
        owner_token=worker_token,
    )

    intent = enqueue_upload_cleanup_intent(
        db_session,
        user_id=user.id,
        object_key=object_key,
        lease_id=lease.id,
        generation=generation,
    )
    assert intent is not None
    assert intent.lease_id == lease.id
    assert intent.generation == generation
    assert intent.status == "pending"


def test_cleanup_intent_insert_conflict_preserves_outer_transaction(
    db_session, monkeypatch
):
    """A savepoint-local insert failure must not roll back caller-owned work."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    user = _make_user(db_session)
    object_key = f"users/{user.id}/{uuid4().hex}.txt"
    unrelated_user = User(
        email=f"unrelated-pending-{uuid4().hex}@example.test",
        hashed_password="test-only-hash",
    )
    db_session.add(unrelated_user)

    original_flush = db_session.flush
    flush_calls = 0

    def fail_intent_insert(*args, **kwargs):
        nonlocal flush_calls
        flush_calls += 1
        # begin_nested() performs its own pre-savepoint flush. Fail only the
        # explicit intent flush inside the savepoint.
        if flush_calls == 2:
            raise IntegrityError("INSERT cleanup intent", {}, Exception("duplicate"))
        return original_flush(*args, **kwargs)

    monkeypatch.setattr(db_session, "flush", fail_intent_insert)

    with pytest.raises(IntegrityError):
        enqueue_upload_cleanup_intent(
            db_session, user_id=user.id, object_key=object_key
        )

    assert db_session.in_transaction()
    assert db_session.get(User, unrelated_user.id) is not None
    assert (
        db_session.query(UploadCleanupIntent)
        .filter(UploadCleanupIntent.object_key == object_key)
        .count()
        == 0
    )


def test_ownerless_cleanup_intent_insert_race_is_idempotent_on_postgres(db_session):
    """Two independent transactions racing on the unique key converge on one intent."""
    import os
    from threading import Barrier, Thread

    import pytest
    from sqlalchemy import event
    from sqlalchemy.orm import Session, sessionmaker

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    if engine.dialect.name != "postgresql":
        pytest.skip("unique-index race behavior requires PostgreSQL")
    if "test" not in (engine.url.database or "").lower():
        pytest.skip("database name is not clearly marked as a test database")
    if os.getenv("ENVIRONMENT", "test").lower() != "test":
        pytest.skip("test environment guard is not active")

    object_key = f"users/orphaned/{uuid4().hex}.txt"
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    insert_barrier = Barrier(2)
    start_barrier = Barrier(2)
    results = []
    errors = []

    def synchronize_intent_insert(session, flush_context, instances):
        if any(
            isinstance(item, UploadCleanupIntent) and item.object_key == object_key
            for item in session.new
        ):
            insert_barrier.wait(timeout=15)

    event.listen(Session, "before_flush", synchronize_intent_insert)
    try:
        def enqueue():
            try:
                with factory() as session:
                    start_barrier.wait(timeout=15)
                    intent = enqueue_upload_cleanup_intent(
                        session, user_id=None, object_key=object_key
                    )
                    assert intent is not None
                    results.append(intent.id)
                    session.commit()
            except BaseException as exc:
                errors.append(exc)

        threads = [Thread(target=enqueue), Thread(target=enqueue)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        assert all(not thread.is_alive() for thread in threads), "enqueue thread hung"
        assert errors == []
        assert len(results) == 2
        assert results[0] == results[1]

        with factory() as verify:
            rows = (
                verify.query(UploadCleanupIntent)
                .filter(UploadCleanupIntent.object_key == object_key)
                .all()
            )
            assert len(rows) == 1
            assert rows[0].status == "pending"
            assert rows[0].attempt_count == 0
    finally:
        event.remove(Session, "before_flush", synchronize_intent_insert)
        with factory() as cleanup:
            cleanup.query(UploadCleanupIntent).filter(
                UploadCleanupIntent.object_key == object_key
            ).delete(synchronize_session=False)
            cleanup.commit()
