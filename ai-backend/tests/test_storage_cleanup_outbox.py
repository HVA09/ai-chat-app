"""Tests for durable storage cleanup processing and safe local paths."""
from datetime import datetime, timedelta, timezone

from app.config import settings as app_settings
from app.models.storage_cleanup_outbox import StorageCleanupOutbox
from app import tasks


def _worker_session_factory(db_session):
    from sqlalchemy.orm import sessionmaker

    connection = db_session.connection()
    factory = sessionmaker(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )
    return factory


def test_storage_cleanup_worker_marks_successful_item_completed(db_session, monkeypatch):
    row = StorageCleanupOutbox(
        operation="delete_user_prefix",
        user_id=987654321,
        status="pending",
        available_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    db_session.add(row)
    db_session.commit()
    row_id = row.id

    monkeypatch.setattr(tasks, "SessionLocal", _worker_session_factory(db_session))
    performed = []
    monkeypatch.setattr(
        tasks,
        "_perform_storage_cleanup",
        lambda *args: performed.append(args),
    )

    assert tasks._run_storage_cleanup_outbox_batch(batch_size=5) == 1
    db_session.expire_all()
    saved = db_session.get(StorageCleanupOutbox, row_id)
    assert saved.status == "completed"
    assert saved.completed_at is not None
    assert saved.attempt_count == 1
    assert len(performed) == 1


def test_storage_cleanup_worker_schedules_retry_after_storage_failure(db_session, monkeypatch):
    row = StorageCleanupOutbox(
        operation="delete_user_prefix",
        user_id=987654322,
        status="pending",
        available_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    db_session.add(row)
    db_session.commit()
    row_id = row.id

    monkeypatch.setattr(tasks, "SessionLocal", _worker_session_factory(db_session))

    def fail_storage(*_args):
        raise OSError("temporary storage outage")

    monkeypatch.setattr(tasks, "_perform_storage_cleanup", fail_storage)

    assert tasks._run_storage_cleanup_outbox_batch(batch_size=5) == 1
    db_session.expire_all()
    saved = db_session.get(StorageCleanupOutbox, row_id)
    assert saved.status == "pending"
    assert saved.locked_at is None
    assert saved.attempt_count == 1
    assert saved.available_at > datetime.now(timezone.utc)
    assert "temporary storage outage" in saved.last_error


def test_storage_cleanup_rejects_local_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    try:
        tasks._storage_cleanup_fallback_path("../outside.txt")
    except RuntimeError as exc:
        assert "escaped UPLOAD_DIR" in str(exc)
    else:
        raise AssertionError("path traversal should be rejected")


def test_local_user_prefix_cleanup_removes_only_user_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    user_dir = tmp_path / "42"
    user_dir.mkdir()
    (user_dir / "upload.bin").write_bytes(b"temporary")
    other_dir = tmp_path / "43"
    other_dir.mkdir()
    (other_dir / "keep.bin").write_bytes(b"keep")

    tasks._perform_storage_cleanup("delete_user_prefix", 42, None, None)

    assert not user_dir.exists()
    assert (other_dir / "keep.bin").exists()


def test_storage_cleanup_worker_recovers_expired_running_lease(db_session, monkeypatch):
    row = StorageCleanupOutbox(
        operation="delete_user_prefix",
        user_id=987654324,
        status="running",
        attempt_count=1,
        available_at=datetime.now(timezone.utc) - timedelta(minutes=16),
        locked_at=datetime.now(timezone.utc) - timedelta(minutes=16),
    )
    db_session.add(row)
    db_session.commit()
    row_id = row.id

    monkeypatch.setattr(tasks, "SessionLocal", _worker_session_factory(db_session))
    performed = []
    monkeypatch.setattr(
        tasks,
        "_perform_storage_cleanup",
        lambda *args: performed.append(args),
    )

    assert tasks._run_storage_cleanup_outbox_batch(batch_size=5) == 1
    db_session.expire_all()
    saved = db_session.get(StorageCleanupOutbox, row_id)
    assert saved.status == "completed"
    assert saved.attempt_count == 2
    assert saved.locked_at is None
    assert len(performed) == 1


def test_local_file_cleanup_is_idempotent_when_object_is_already_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    for name in ("S3_BUCKET", "S3_ENDPOINT_URL", "S3_REGION", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.setattr(app_settings, name, None)

    missing_path = "42/already-deleted.txt"
    tasks._perform_storage_cleanup("delete_file", None, "users/42/already-deleted.txt", missing_path)
    tasks._perform_storage_cleanup("delete_file", None, "users/42/already-deleted.txt", missing_path)
    assert not (tmp_path / missing_path).exists()

def test_storage_cleanup_moves_repeated_failures_to_dead_letter(db_session, monkeypatch):
    row = StorageCleanupOutbox(
        operation="delete_user_prefix",
        user_id=987654323,
        status="pending",
        attempt_count=11,
        available_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    db_session.add(row)
    db_session.commit()
    row_id = row.id

    monkeypatch.setattr(tasks, "SessionLocal", _worker_session_factory(db_session))
    monkeypatch.setattr(
        tasks,
        "_perform_storage_cleanup",
        lambda *_args: (_ for _ in ()).throw(OSError("persistent storage failure")),
    )

    assert tasks._run_storage_cleanup_outbox_batch(batch_size=5) == 1
    db_session.expire_all()
    saved = db_session.get(StorageCleanupOutbox, row_id)
    assert saved.status == "failed"
    assert saved.attempt_count == 12
    assert saved.locked_at is None
