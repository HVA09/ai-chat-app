"""Tests for reader-lease streaming lifecycle."""
from threading import Event, Thread
import time

import pytest

from app.services import file_read_leases


class BlockingBody:
    def __init__(self):
        self.started = Event()
        self.resume = Event()
        self.closed = False
        self.finished = False

    def __iter__(self):
        return self

    def __next__(self):
        if self.finished:
            raise StopIteration
        self.started.set()
        self.resume.wait(timeout=2)
        self.finished = True
        if self.closed:
            raise StopIteration
        return b"chunk"

    def close(self):
        self.closed = True
        self.resume.set()


def test_stream_lease_heartbeat_runs_while_storage_read_is_blocked(monkeypatch):
    body = BlockingBody()
    renewals = []
    releases = []
    monkeypatch.setattr(
        file_read_leases,
        "renew_file_read_lease",
        lambda lease_id: renewals.append(lease_id) or True,
    )
    monkeypatch.setattr(
        file_read_leases,
        "release_file_read_lease",
        lambda lease_id: releases.append(lease_id),
    )

    stream = file_read_leases.stream_file_with_lease(body, "lease-1", heartbeat_interval=0.01)
    received = []
    consumer = Thread(target=lambda: received.extend(stream))
    consumer.start()
    assert body.started.wait(timeout=1)
    time.sleep(0.06)
    assert renewals
    body.resume.set()
    consumer.join(timeout=1)

    assert not consumer.is_alive()
    assert received == [b"chunk"]
    assert releases == ["lease-1"]
    assert body.closed


def test_stream_stops_when_lease_heartbeat_cannot_renew(monkeypatch):
    body = BlockingBody()
    releases = []
    monkeypatch.setattr(file_read_leases, "renew_file_read_lease", lambda _lease_id: False)
    monkeypatch.setattr(
        file_read_leases,
        "release_file_read_lease",
        lambda lease_id: releases.append(lease_id),
    )
    stream = file_read_leases.stream_file_with_lease(body, "lease-2", heartbeat_interval=0.01)
    errors = []

    def consume():
        try:
            list(stream)
        except RuntimeError as exc:
            errors.append(str(exc))

    consumer = Thread(target=consume)
    consumer.start()
    assert body.started.wait(timeout=1)
    consumer.join(timeout=1)

    assert not consumer.is_alive()
    assert body.closed
    assert errors == ["File read lease could not be renewed"]
    assert releases == ["lease-2"]



def test_stream_keeps_lease_when_heartbeat_worker_does_not_stop(monkeypatch):
    body = BlockingBody()
    releases = []

    class StuckWorker:
        def __init__(self, **_kwargs):
            pass

        def start(self):
            return None

        def join(self, timeout=None):
            assert timeout == 2.0

        def is_alive(self):
            return True

    monkeypatch.setattr(file_read_leases, "Thread", StuckWorker)
    monkeypatch.setattr(
        file_read_leases,
        "release_file_read_lease",
        lambda lease_id: releases.append(lease_id),
    )

    stream = file_read_leases.stream_file_with_lease(
        body, "lease-stuck-heartbeat", heartbeat_interval=0.01
    )
    assert list(stream) == [b"chunk"]
    assert body.closed
    # The lease is deliberately retained until expiry: releasing it while
    # renewal may still be in flight could let cleanup race a live reader.
    assert releases == []



def test_committed_account_deletion_preserves_reader_lease_until_prefix_cleanup(
    db_session, monkeypatch,
):
    """Verify durable lease evidence across account cascades using committed sessions."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy.orm import sessionmaker

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    from app.models.file_attachment import FileAttachment

    # Use the same test-configured engine as the suite, but independent,
    # committed sessions rather than importing pytest's conftest module.
    TestingSessionLocal = sessionmaker(
        bind=engine, autocommit=False, autoflush=False
    )
    from app.models.file_attachment_read_lease import FileAttachmentReadLease
    from app.models.user import User
    from app.routers import users as users_router
    from app.schemas.user import DeleteAccountRequest
    from app.services import file_read_leases
    from app.tasks import _perform_storage_cleanup

    monkeypatch.setattr(file_read_leases, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(users_router, "verify_password", lambda *_args: True)
    monkeypatch.setattr(users_router, "dispatch_storage_cleanup", lambda: None)

    setup_db = TestingSessionLocal()
    user = User(
        email="reader-lease-account-delete@example.com",
        hashed_password="test-hash",
    )
    setup_db.add(user)
    setup_db.flush()
    attachment = FileAttachment(
        user_id=user.id,
        original_filename="active.txt",
        stored_filename="reader-lease-account-delete.txt",
        object_key=f"users/{user.id}/reader-lease-account-delete.txt",
        content_type="text/plain",
        size_bytes=12,
    )
    setup_db.add(attachment)
    setup_db.flush()
    user_id = user.id
    setup_db.add(
        FileAttachmentReadLease(
            id="committed-account-delete-lease",
            file_attachment_id=attachment.id,
            user_id=user_id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
    )
    setup_db.commit()
    setup_db.close()

    delete_db = TestingSessionLocal()
    try:
        deleting_user = delete_db.get(User, user_id)
        assert deleting_user is not None
        users_router.delete_account(
            DeleteAccountRequest(password="verified-by-test"),
            deleting_user,
            delete_db,
        )
    finally:
        delete_db.close()

    verify_db = TestingSessionLocal()
    try:
        assert verify_db.get(User, user_id) is None
        assert verify_db.query(FileAttachment).filter(
            FileAttachment.user_id == user_id
        ).count() == 0
        lease = verify_db.get(
            FileAttachmentReadLease, "committed-account-delete-lease"
        )
        assert lease is not None
        assert lease.user_id == user_id
    finally:
        verify_db.close()

    with pytest.raises(file_read_leases.ActiveFileReadLeaseError):
        _perform_storage_cleanup("delete_user_prefix", user_id, None, None)

    assert file_read_leases.has_active_user_read_leases(user_id) is True


def test_account_delete_waits_for_inflight_reader_lease_acquisition_on_postgres(
    db_session, monkeypatch,
):
    """A reader that locks the attachment first commits its lease before account cascades."""
    from datetime import datetime, timedelta, timezone
    from threading import Event, Thread
    from uuid import uuid4

    from sqlalchemy.orm import sessionmaker

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    from app.models.file_attachment import FileAttachment
    from app.models.file_attachment_read_lease import FileAttachmentReadLease
    from app.models.user import User
    from app.routers import users as users_router
    from app.schemas.user import DeleteAccountRequest
    from app.services import file_read_leases
    from app.tasks import _perform_storage_cleanup

    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock behavior is required for this concurrency test")

    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(file_read_leases, "SessionLocal", session_factory)
    monkeypatch.setattr(users_router, "verify_password", lambda *_args: True)
    monkeypatch.setattr(users_router, "dispatch_storage_cleanup", lambda: None)

    suffix = uuid4().hex
    setup_db = session_factory()
    user = User(
        email=f"reader-delete-race-{suffix}@example.test",
        hashed_password="test-only-hash",
    )
    setup_db.add(user)
    setup_db.flush()
    attachment = FileAttachment(
        user_id=user.id,
        original_filename="racing-reader.txt",
        stored_filename="racing-reader.txt",
        object_key=f"users/{user.id}/racing-reader.txt",
        content_type="text/plain",
        size_bytes=12,
    )
    setup_db.add(attachment)
    setup_db.commit()
    user_id, file_id = user.id, attachment.id
    setup_db.close()

    lease_locked_attachment = Event()
    allow_lease_commit = Event()
    delete_finished = Event()
    delete_lock_attempted = Event()
    lease_errors = []
    delete_errors = []
    lease_ids = []

    def acquire_and_commit_lease():
        try:
            with session_factory() as lease_db:
                lease_id = file_read_leases.acquire_file_read_lease(file_id, lease_db)
                lease_ids.append(lease_id)
                lease_locked_attachment.set()
                if not allow_lease_commit.wait(10):
                    raise TimeoutError("lease test did not release the attachment lock")
                lease_db.commit()
        except BaseException as exc:
            lease_errors.append(exc)

    def delete_account():
        try:
            with session_factory() as delete_db:
                from sqlalchemy import event

                connection = delete_db.connection()

                def observe_user_lock(_conn, _cursor, statement, _parameters, _context, _many):
                    normalized = statement.lower()
                    if "for update" in normalized and "users" in normalized:
                        delete_lock_attempted.set()

                event.listen(connection, "before_cursor_execute", observe_user_lock)
                deleting_user = delete_db.get(User, user_id)
                users_router.delete_account(
                    DeleteAccountRequest(password="verified-by-test"),
                    deleting_user,
                    delete_db,
                )
        except BaseException as exc:
            delete_errors.append(exc)
        finally:
            delete_finished.set()

    lease_thread = Thread(target=acquire_and_commit_lease, daemon=True)
    delete_thread = Thread(target=delete_account, daemon=True)
    try:
        lease_thread.start()
        assert lease_locked_attachment.wait(10), "reader did not lock the attachment"

        delete_thread.start()
        assert delete_lock_attempted.wait(10), "account deletion did not attempt the user row lock"
        # The deletion must wait at the same user-row lock held by the reader.
        # Observe the actual SQL lock attempt instead of waiting for before_commit,
        # which cannot run until the reader releases its lock.
        assert not delete_finished.wait(0.2), "account deletion bypassed the user row lock"

        allow_lease_commit.set()
        lease_thread.join(timeout=10)
        delete_thread.join(timeout=10)
        assert not lease_thread.is_alive()
        assert not delete_thread.is_alive()
        assert lease_errors == []
        assert delete_errors == []
        assert len(lease_ids) == 1

        with session_factory() as verify_db:
            assert verify_db.get(User, user_id) is None
            assert verify_db.get(FileAttachment, file_id) is None
            lease = verify_db.get(FileAttachmentReadLease, lease_ids[0])
            assert lease is not None
            assert lease.user_id == user_id
            assert lease.expires_at > datetime.now(timezone.utc)

        with pytest.raises(file_read_leases.ActiveFileReadLeaseError):
            _perform_storage_cleanup("delete_user_prefix", user_id, None, None)
        assert file_read_leases.has_active_user_read_leases(user_id) is True
    finally:
        allow_lease_commit.set()
        lease_thread.join(timeout=10)
        delete_thread.join(timeout=10)
        with session_factory() as cleanup_db:
            cleanup_db.query(FileAttachmentReadLease).filter(
                FileAttachmentReadLease.user_id == user_id
            ).delete()
            cleanup_db.query(User).filter(User.id == user_id).delete()
            cleanup_db.commit()

def test_asgi_client_disconnect_closes_stream_and_releases_reader_lease(monkeypatch):
    """The response must close the lease-owning iterator when ASGI send disconnects."""
    import asyncio

    from starlette.requests import ClientDisconnect

    from app.routers.files import LeaseAwareStreamingResponse

    body = BlockingBody()
    body.resume.set()
    releases = []
    monkeypatch.setattr(
        file_read_leases,
        "renew_file_read_lease",
        lambda _lease_id: True,
    )
    monkeypatch.setattr(
        file_read_leases,
        "release_file_read_lease",
        lambda lease_id: releases.append(lease_id),
    )

    stream = file_read_leases.stream_file_with_lease(
        body, "lease-asgi-disconnect", heartbeat_interval=60
    )
    response = LeaseAwareStreamingResponse(stream, media_type="text/plain")

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        if message["type"] == "http.response.body":
            raise OSError("simulated client disconnect")

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/files/1",
        "raw_path": b"/files/1",
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("testclient", 12345),
        "state": {},
    }

    with pytest.raises(ClientDisconnect):
        asyncio.run(response(scope, receive, send))

    assert body.closed
    assert releases == ["lease-asgi-disconnect"]

def test_lease_renewal_applies_postgres_statement_timeout(monkeypatch):
    calls = []

    class Bind:
        class dialect:
            name = "postgresql"

    class Result:
        rowcount = 1

    class FakeSession:
        def get_bind(self):
            return Bind()

        def execute(self, statement):
            calls.append(str(statement))
            return None if len(calls) == 1 else Result()

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(file_read_leases, "SessionLocal", FakeSession)

    assert file_read_leases.renew_file_read_lease("lease-timeout") is True
    assert calls[0] == "SET LOCAL statement_timeout = '10s'"
    assert "UPDATE file_attachment_read_leases" in calls[1]

def test_account_delete_wins_before_reader_lease_acquisition_on_postgres(
    db_session, monkeypatch,
):
    """A reader waiting behind the account cascade cannot lease a deleted attachment."""
    from threading import Event, Thread
    from uuid import uuid4

    from sqlalchemy import event, text
    from sqlalchemy.orm import sessionmaker

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock behavior is required for this concurrency test")

    from app.models.file_attachment import FileAttachment
    from app.models.file_attachment_read_lease import FileAttachmentReadLease
    from app.models.user import User
    from app.routers import users as users_router
    from app.schemas.user import DeleteAccountRequest
    from app.services import file_read_leases

    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(users_router, "verify_password", lambda *_args: True)
    monkeypatch.setattr(users_router, "dispatch_storage_cleanup", lambda: None)

    suffix = uuid4().hex
    with session_factory() as setup_db:
        user = User(
            email=f"delete-reader-race-{suffix}@example.test",
            hashed_password="test-only-hash",
        )
        setup_db.add(user)
        setup_db.flush()
        attachment = FileAttachment(
            user_id=user.id,
            original_filename="delete-wins.txt",
            stored_filename="delete-wins.txt",
            object_key=f"users/{user.id}/delete-wins.txt",
            content_type="text/plain",
            size_bytes=12,
        )
        setup_db.add(attachment)
        setup_db.commit()
        user_id, file_id = user.id, attachment.id

    deletion_flushed = Event()
    allow_delete_commit = Event()
    delete_finished = Event()
    reader_user_lock_attempted = Event()
    delete_backend_pids = []
    reader_backend_pids = []
    delete_errors = []
    acquisition_errors = []
    acquired_lease_ids = []

    def delete_account():
        try:
            with session_factory() as delete_db:
                delete_backend_pids.append(
                    delete_db.connection().exec_driver_sql("SELECT pg_backend_pid()").scalar_one()
                )

                def flush_and_pause(session):
                    # Hold the deleted user's row lock while the reader reaches
                    # its competing SELECT ... FOR UPDATE.
                    session.flush()
                    deletion_flushed.set()
                    if not allow_delete_commit.wait(10):
                        raise TimeoutError("reader test did not release account deletion")

                event.listen(delete_db, "before_commit", flush_and_pause, once=True)
                deleting_user = delete_db.get(User, user_id)
                users_router.delete_account(
                    DeleteAccountRequest(password="verified-by-test"),
                    deleting_user,
                    delete_db,
                )
        except BaseException as exc:
            delete_errors.append(exc)
        finally:
            delete_finished.set()

    def acquire_lease():
        try:
            with session_factory() as lease_db:
                connection = lease_db.connection()
                reader_backend_pids.append(
                    connection.exec_driver_sql("SELECT pg_backend_pid()").scalar_one()
                )

                def observe_user_lock(_conn, _cursor, statement, _parameters, _context, _many):
                    normalized = statement.lower()
                    if "for update" in normalized and "users" in normalized:
                        reader_user_lock_attempted.set()

                event.listen(connection, "before_cursor_execute", observe_user_lock)
                acquired_lease_ids.append(
                    file_read_leases.acquire_file_read_lease(file_id, lease_db)
                )
                lease_db.commit()
        except BaseException as exc:
            acquisition_errors.append(exc)

    delete_thread = Thread(target=delete_account, daemon=True)
    reader_thread = Thread(target=acquire_lease, daemon=True)
    try:
        delete_thread.start()
        assert deletion_flushed.wait(10), "account cascade did not flush"
        reader_thread.start()
        assert reader_user_lock_attempted.wait(10), "reader did not attempt the owner row lock"

        # Do not infer lock contention from SQLAlchemy's pre-execution event.
        # PostgreSQL itself must report that the reader backend is blocked by
        # the still-uncommitted account-deletion transaction.
        deadline = time.monotonic() + 10
        reader_is_blocked_by_delete = False
        while time.monotonic() < deadline:
            with engine.connect() as observer:
                blockers = observer.execute(
                    text("SELECT pg_blocking_pids(:reader_pid)"),
                    {"reader_pid": reader_backend_pids[0]},
                ).scalar_one()
            if delete_backend_pids[0] in blockers:
                reader_is_blocked_by_delete = True
                break
            time.sleep(0.02)
        assert reader_is_blocked_by_delete, (
            "PostgreSQL did not report the reader waiting on the account-deletion row lock"
        )

        allow_delete_commit.set()
        delete_thread.join(timeout=10)
        reader_thread.join(timeout=10)
        assert not delete_thread.is_alive()
        assert not reader_thread.is_alive()
        assert delete_errors == []
        assert len(acquisition_errors) == 1
        assert isinstance(acquisition_errors[0], file_read_leases.FileUnavailableError)
        assert acquired_lease_ids == []

        with session_factory() as verify_db:
            assert verify_db.get(User, user_id) is None
            assert verify_db.get(FileAttachment, file_id) is None
            assert (
                verify_db.query(FileAttachmentReadLease)
                .filter(FileAttachmentReadLease.file_attachment_id == file_id)
                .count()
                == 0
            )
    finally:
        allow_delete_commit.set()
        delete_thread.join(timeout=10)
        reader_thread.join(timeout=10)
        with session_factory() as cleanup_db:
            cleanup_db.query(FileAttachmentReadLease).filter(
                FileAttachmentReadLease.file_attachment_id == file_id
            ).delete()
            cleanup_db.query(User).filter(User.id == user_id).delete()
            cleanup_db.commit()
