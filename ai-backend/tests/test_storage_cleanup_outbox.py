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


def test_stale_worker_cannot_mark_reclaimed_item_completed(db_session, monkeypatch):
    row = StorageCleanupOutbox(
        operation="delete_user_prefix",
        user_id=987654325,
        status="pending",
        available_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    db_session.add(row)
    db_session.commit()
    row_id = row.id
    monkeypatch.setattr(tasks, "SessionLocal", _worker_session_factory(db_session))

    def reclaim_during_storage_io(*_args):
        current = db_session.get(StorageCleanupOutbox, row_id)
        current.status = "running"
        current.lease_token = "worker-b-lease"
        current.locked_at = datetime.now(timezone.utc)
        db_session.commit()

    monkeypatch.setattr(tasks, "_perform_storage_cleanup", reclaim_during_storage_io)
    assert tasks._run_storage_cleanup_outbox_batch(batch_size=1) == 1
    db_session.expire_all()
    saved = db_session.get(StorageCleanupOutbox, row_id)
    assert saved.status == "running"
    assert saved.lease_token == "worker-b-lease"
    assert saved.completed_at is None


def test_stale_worker_cannot_schedule_retry_after_lease_reclaim(db_session, monkeypatch):
    row = StorageCleanupOutbox(
        operation="delete_user_prefix",
        user_id=987654326,
        status="pending",
        available_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    db_session.add(row)
    db_session.commit()
    row_id = row.id
    monkeypatch.setattr(tasks, "SessionLocal", _worker_session_factory(db_session))

    def reclaim_then_fail(*_args):
        current = db_session.get(StorageCleanupOutbox, row_id)
        current.status = "running"
        current.lease_token = "worker-b-lease"
        current.locked_at = datetime.now(timezone.utc)
        db_session.commit()
        raise OSError("stale worker failure")

    monkeypatch.setattr(tasks, "_perform_storage_cleanup", reclaim_then_fail)
    assert tasks._run_storage_cleanup_outbox_batch(batch_size=1) == 1
    db_session.expire_all()
    saved = db_session.get(StorageCleanupOutbox, row_id)
    assert saved.status == "running"
    assert saved.lease_token == "worker-b-lease"
    assert saved.last_error is None


def test_postgres_independent_workers_reclaim_and_fence_stale_completion(monkeypatch):
    """Exercise A/B lease reclaim through separate PostgreSQL sessions."""
    from app.database import SessionLocal as IndependentSessionLocal

    row = StorageCleanupOutbox(
        operation="delete_user_prefix",
        user_id=987654327,
        status="pending",
        available_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    with IndependentSessionLocal() as setup_db:
        setup_db.add(row)
        setup_db.commit()
        row_id = row.id

    monkeypatch.setattr(tasks, "SessionLocal", IndependentSessionLocal)
    calls = {"count": 0}

    def storage_io(*_args):
        calls["count"] += 1
        if calls["count"] == 1:
            # Expire A's lease from another independent connection, then let B
            # reclaim and finish the same row before A attempts its completion.
            with IndependentSessionLocal() as expiry_db:
                current = expiry_db.get(StorageCleanupOutbox, row_id)
                current.locked_at = datetime.now(timezone.utc) - timedelta(minutes=16)
                expiry_db.commit()
            assert tasks._run_storage_cleanup_outbox_batch(batch_size=1) == 1

    monkeypatch.setattr(tasks, "_perform_storage_cleanup", storage_io)
    assert tasks._run_storage_cleanup_outbox_batch(batch_size=1) == 1
    assert calls["count"] == 2

    with IndependentSessionLocal() as verify_db:
        saved = verify_db.get(StorageCleanupOutbox, row_id)
        assert saved.status == "completed"
        assert saved.attempt_count == 2
        assert saved.lease_token is None
        assert saved.completed_at is not None


def test_postgres_independent_workers_ignore_stale_failure_after_reclaim(monkeypatch):
    """A's late failure must not overwrite B's successful completion."""
    from app.database import SessionLocal as IndependentSessionLocal

    row = StorageCleanupOutbox(
        operation="delete_user_prefix",
        user_id=987654328,
        status="pending",
        available_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    with IndependentSessionLocal() as setup_db:
        setup_db.add(row)
        setup_db.commit()
        row_id = row.id

    monkeypatch.setattr(tasks, "SessionLocal", IndependentSessionLocal)
    calls = {"count": 0}

    def storage_io(*_args):
        calls["count"] += 1
        if calls["count"] == 1:
            with IndependentSessionLocal() as expiry_db:
                current = expiry_db.get(StorageCleanupOutbox, row_id)
                current.locked_at = datetime.now(timezone.utc) - timedelta(minutes=16)
                expiry_db.commit()
            assert tasks._run_storage_cleanup_outbox_batch(batch_size=1) == 1
            raise OSError("late stale worker failure")

    monkeypatch.setattr(tasks, "_perform_storage_cleanup", storage_io)
    assert tasks._run_storage_cleanup_outbox_batch(batch_size=1) == 1
    assert calls["count"] == 2

    with IndependentSessionLocal() as verify_db:
        saved = verify_db.get(StorageCleanupOutbox, row_id)
        assert saved.status == "completed"
        assert saved.attempt_count == 2
        assert saved.lease_token is None
        assert saved.last_error is None
        assert saved.completed_at is not None



def test_postgres_two_workers_claim_distinct_outbox_rows_concurrently(monkeypatch):
    """Two real worker threads should claim separate due rows without duplication."""
    from threading import Barrier, Thread

    import pytest
    from app.database import SessionLocal as IndependentSessionLocal

    with IndependentSessionLocal() as setup_db:
        if setup_db.get_bind().dialect.name != "postgresql":
            pytest.skip("PostgreSQL SKIP LOCKED behavior is required")
        rows = [
            StorageCleanupOutbox(
                operation="delete_user_prefix",
                user_id=987654329 + index,
                status="pending",
                available_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            )
            for index in range(2)
        ]
        setup_db.add_all(rows)
        setup_db.commit()
        row_ids = [row.id for row in rows]

    monkeypatch.setattr(tasks, "SessionLocal", IndependentSessionLocal)
    storage_barrier = Barrier(2)
    claimed_user_ids = []
    worker_results = []
    worker_errors = []

    def fake_storage_cleanup(_operation, user_id, _object_key, _fallback_path):
        claimed_user_ids.append(user_id)
        storage_barrier.wait(timeout=15)

    def run_worker():
        try:
            worker_results.append(tasks._run_storage_cleanup_outbox_batch(batch_size=1))
        except BaseException as exc:
            worker_errors.append(exc)

    monkeypatch.setattr(tasks, "_perform_storage_cleanup", fake_storage_cleanup)
    workers = [Thread(target=run_worker, daemon=True) for _ in range(2)]
    try:
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=25)

        assert all(not worker.is_alive() for worker in workers), "workers did not finish"
        assert worker_errors == []
        assert worker_results == [1, 1]
        assert sorted(claimed_user_ids) == [987654329, 987654330]
        with IndependentSessionLocal() as verify_db:
            saved = (
                verify_db.query(StorageCleanupOutbox)
                .filter(StorageCleanupOutbox.id.in_(row_ids))
                .order_by(StorageCleanupOutbox.id)
                .all()
            )
            assert len(saved) == 2
            assert all(row.status == "completed" for row in saved)
            assert all(row.attempt_count == 1 for row in saved)
    finally:
        storage_barrier.abort()
        for worker in workers:
            worker.join(timeout=5)
        with IndependentSessionLocal() as cleanup_db:
            cleanup_db.query(StorageCleanupOutbox).filter(
                StorageCleanupOutbox.id.in_(row_ids)
            ).delete(synchronize_session=False)
            cleanup_db.commit()



def test_postgres_recovers_after_storage_cleanup_succeeds_but_completion_commit_fails(monkeypatch):
    """An expired lease retries idempotent cleanup if completion could not persist."""
    import pytest
    from app.database import SessionLocal as IndependentSessionLocal

    with IndependentSessionLocal() as setup_db:
        if setup_db.get_bind().dialect.name != "postgresql":
            pytest.skip("Independent PostgreSQL sessions are required")
        row = StorageCleanupOutbox(
            operation="delete_user_prefix",
            user_id=987654331,
            status="pending",
            available_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        setup_db.add(row)
        setup_db.commit()
        row_id = row.id

    try:
        session_count = {"value": 0}

        def fail_completion_commit_once():
            session = IndependentSessionLocal()
            session_count["value"] += 1
            if session_count["value"] == 2:
                original_commit = session.commit

                def fail_once():
                    session.commit = original_commit
                    raise OSError("simulated completion persistence failure")

                session.commit = fail_once
            return session

        cleanup_calls = []
        monkeypatch.setattr(tasks, "SessionLocal", fail_completion_commit_once)
        monkeypatch.setattr(
            tasks,
            "_perform_storage_cleanup",
            lambda *args: cleanup_calls.append(args),
        )

        assert tasks._run_storage_cleanup_outbox_batch(batch_size=1) == 1
        with IndependentSessionLocal() as verify_db:
            saved = verify_db.get(StorageCleanupOutbox, row_id)
            assert saved.status == "running"
            assert saved.lease_token
            assert saved.completed_at is None

        # Simulate the worker being unavailable until its 15-minute lease expires.
        with IndependentSessionLocal() as expiry_db:
            saved = expiry_db.get(StorageCleanupOutbox, row_id)
            saved.locked_at = datetime.now(timezone.utc) - timedelta(minutes=16)
            expiry_db.commit()

        monkeypatch.setattr(tasks, "SessionLocal", IndependentSessionLocal)
        assert tasks._run_storage_cleanup_outbox_batch(batch_size=1) == 1
        assert len(cleanup_calls) == 2

        with IndependentSessionLocal() as verify_db:
            saved = verify_db.get(StorageCleanupOutbox, row_id)
            assert saved.status == "completed"
            assert saved.attempt_count == 2
            assert saved.lease_token is None
            assert saved.completed_at is not None

    finally:
        with IndependentSessionLocal() as cleanup_db:
            cleanup_db.query(StorageCleanupOutbox).filter(
                StorageCleanupOutbox.id == row_id
            ).delete(synchronize_session=False)
            cleanup_db.commit()
