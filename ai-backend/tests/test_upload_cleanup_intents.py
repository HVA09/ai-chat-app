from uuid import uuid4

from app.models.file_attachment import FileAttachment
from app.models.upload_cleanup_intent import UploadCleanupIntent
from app.models.user import User
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


def test_cleanup_intent_insert_failure_preserves_callers_transaction(db_session, monkeypatch):
    from sqlalchemy.exc import IntegrityError

    user = _make_user(db_session)
    original_flush = db_session.flush
    raised = False

    def fail_cleanup_insert(*args, **kwargs):
        nonlocal raised
        if not raised and any(
            isinstance(item, UploadCleanupIntent) for item in db_session.new
        ):
            raised = True
            raise IntegrityError("simulated unique-key race", {}, Exception("duplicate"))
        return original_flush(*args, **kwargs)

    monkeypatch.setattr(db_session, "flush", fail_cleanup_insert)
    try:
        enqueue_upload_cleanup_intent(
            db_session,
            user_id=user.id,
            object_key=f"users/{user.id}/{uuid4().hex}.txt",
        )
        assert False, "expected the simulated insert failure"
    except IntegrityError:
        pass

    # The failed insert must not roll back the caller's existing transaction.
    another_user = _make_user(db_session)
    assert another_user.id is not None
    db_session.commit()
