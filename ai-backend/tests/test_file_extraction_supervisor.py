"""Tests for the spawned parser supervisor primitive."""
from pathlib import Path

import pytest

from app.services.file_extraction_supervisor import (
    ExtractionSupervisorError,
    extract_text_isolated,
)
from app.services.file_text_extractor import FileTextExtractionError


def test_isolated_extractor_returns_bounded_text(tmp_path: Path):
    source = tmp_path / "source.txt"
    source.write_text("Linux, networking, and cloud", encoding="utf-8")

    result = extract_text_isolated(
        source,
        "text/plain",
        max_chars=128,
        timeout_seconds=5,
        heartbeat_interval_seconds=1,
    )

    assert result == "Linux, networking, and cloud"


def test_isolated_extractor_returns_none_for_unsupported_content_type(
    tmp_path: Path,
):
    source = tmp_path / "image.bin"
    source.write_bytes(b"not text")

    result = extract_text_isolated(
        source,
        "application/octet-stream",
        timeout_seconds=5,
        heartbeat_interval_seconds=1,
    )

    assert result is None


def test_isolated_extractor_rejects_invalid_timing_before_spawn(
    tmp_path: Path,
):
    source = tmp_path / "source.txt"
    source.write_text("safe", encoding="utf-8")

    with pytest.raises(ExtractionSupervisorError, match="invalid_supervisor_timing"):
        extract_text_isolated(
            source,
            "text/plain",
            timeout_seconds=1,
            heartbeat_interval_seconds=1,
        )


def test_isolated_extractor_reports_parser_failure_without_details(
    tmp_path: Path,
):
    source = tmp_path / "broken.pdf"
    source.write_bytes(b"not a valid PDF")

    with pytest.raises(FileTextExtractionError):
        extract_text_isolated(
            source,
            "application/pdf",
            timeout_seconds=5,
            heartbeat_interval_seconds=1,
        )



class _FakeConnection:
    def poll(self, _timeout):
        return False

    def close(self):
        pass


class _FakeProcess:
    def __init__(self, *, stops_on_terminate):
        self.alive = True
        self.exitcode = None
        self.stops_on_terminate = stops_on_terminate
        self.terminate_calls = 0
        self.kill_calls = 0
        self.closed = False

    def start(self):
        pass

    def is_alive(self):
        return self.alive

    def terminate(self):
        self.terminate_calls += 1
        if self.stops_on_terminate:
            self.alive = False
            self.exitcode = -15

    def kill(self):
        self.kill_calls += 1
        if self.stops_on_terminate:
            self.alive = False
            self.exitcode = -9

    def join(self, _timeout=None):
        pass

    def close(self):
        assert not self.alive
        self.closed = True


class _FakeSpawnContext:
    def __init__(self, process):
        self.process = process

    def Pipe(self, duplex=False):
        assert duplex is False
        return _FakeConnection(), _FakeConnection()

    def Process(self, **_kwargs):
        return self.process


def test_heartbeat_loss_stops_and_reaps_parser_before_returning(
    tmp_path: Path, monkeypatch
):
    from app.services import file_extraction_supervisor as supervisor

    source = tmp_path / "source.txt"
    source.write_text("safe", encoding="utf-8")
    process = _FakeProcess(stops_on_terminate=True)
    monkeypatch.setattr(
        supervisor.multiprocessing,
        "get_context",
        lambda _method: _FakeSpawnContext(process),
    )

    with pytest.raises(ExtractionSupervisorError, match="heartbeat_lost"):
        extract_text_isolated(
            source,
            "text/plain",
            heartbeat=lambda: False,
            timeout_seconds=1,
            heartbeat_interval_seconds=0.001,
        )

    assert process.terminate_calls == 1
    assert process.kill_calls == 0
    assert process.closed is True
    assert process.alive is False


def test_unverified_child_stop_preserves_exact_materialized_source(
    tmp_path: Path, monkeypatch
):
    from app.services import file_extraction_supervisor as supervisor
    from app.services.storage import PreserveMaterializedFile

    source = tmp_path / "source.txt"
    source.write_text("must remain available", encoding="utf-8")
    process = _FakeProcess(stops_on_terminate=False)
    monkeypatch.setattr(
        supervisor.multiprocessing,
        "get_context",
        lambda _method: _FakeSpawnContext(process),
    )

    with pytest.raises(PreserveMaterializedFile) as raised:
        extract_text_isolated(
            source,
            "text/plain",
            heartbeat=lambda: False,
            timeout_seconds=1,
            heartbeat_interval_seconds=0.001,
        )

    assert raised.value.path == source
    assert source.read_text(encoding="utf-8") == "must remain available"
    assert process.terminate_calls >= 1
    assert process.kill_calls >= 1
    assert process.alive is True
    assert process.closed is False

class _ResultConnection(_FakeConnection):
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.closed = False

    def poll(self, _timeout):
        return True

    def recv_bytes(self, _maxlength):
        if self.error is not None:
            raise self.error
        return self.payload

    def close(self):
        self.closed = True


class _ResultSpawnContext(_FakeSpawnContext):
    def __init__(self, process, receive_connection):
        super().__init__(process)
        self.receive_connection = receive_connection

    def Pipe(self, duplex=False):
        assert duplex is False
        return self.receive_connection, _FakeConnection()


def test_parser_timeout_stops_and_reaps_child(monkeypatch, tmp_path: Path):
    from app.services import file_extraction_supervisor as supervisor

    source = tmp_path / "source.txt"
    source.write_text("safe", encoding="utf-8")
    process = _FakeProcess(stops_on_terminate=True)
    connection = _FakeConnection()
    monkeypatch.setattr(
        supervisor.multiprocessing,
        "get_context",
        lambda _method: _ResultSpawnContext(process, connection),
    )
    ticks = iter((1.0, 2.0, 3.0))
    monkeypatch.setattr(supervisor.time, "monotonic", lambda: next(ticks))

    with pytest.raises(ExtractionSupervisorError, match="parser_timeout"):
        extract_text_isolated(
            source,
            "text/plain",
            timeout_seconds=1,
            heartbeat_interval_seconds=0.5,
        )

    assert process.terminate_calls == 1
    assert process.alive is False
    assert process.closed is True


def test_child_exit_without_result_is_rejected(monkeypatch, tmp_path: Path):
    from app.services import file_extraction_supervisor as supervisor

    source = tmp_path / "source.txt"
    source.write_text("safe", encoding="utf-8")
    process = _FakeProcess(stops_on_terminate=True)
    process.alive = False
    process.exitcode = 2
    connection = _FakeConnection()
    monkeypatch.setattr(
        supervisor.multiprocessing,
        "get_context",
        lambda _method: _ResultSpawnContext(process, connection),
    )

    with pytest.raises(
        ExtractionSupervisorError, match="parser_exited_without_result"
    ):
        extract_text_isolated(
            source,
            "text/plain",
            timeout_seconds=5,
            heartbeat_interval_seconds=1,
        )

    assert process.closed is True


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        (b"{not-json", None),
        (None, OSError("oversized IPC frame")),
    ],
)
def test_invalid_or_oversized_parser_ipc_is_rejected(
    monkeypatch, tmp_path: Path, payload, error
):
    from app.services import file_extraction_supervisor as supervisor

    source = tmp_path / "source.txt"
    source.write_text("safe", encoding="utf-8")
    process = _FakeProcess(stops_on_terminate=True)
    process.alive = False
    process.exitcode = 0
    connection = _ResultConnection(payload=payload, error=error)
    monkeypatch.setattr(
        supervisor.multiprocessing,
        "get_context",
        lambda _method: _ResultSpawnContext(process, connection),
    )

    with pytest.raises(ExtractionSupervisorError, match="parser_result_invalid"):
        extract_text_isolated(
            source,
            "text/plain",
            timeout_seconds=5,
            heartbeat_interval_seconds=1,
        )

    assert connection.closed is True
    assert process.closed is True


def test_process_start_failure_closes_both_pipe_ends(monkeypatch, tmp_path: Path):
    from app.services import file_extraction_supervisor as supervisor

    class _StartFailureProcess(_FakeProcess):
        def start(self):
            raise OSError("process creation failed")

    class _TrackedConnection(_FakeConnection):
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    class _TrackedContext(_FakeSpawnContext):
        def Pipe(self, duplex=False):
            assert duplex is False
            self.receive = _TrackedConnection()
            self.send = _TrackedConnection()
            return self.receive, self.send

    source = tmp_path / "source.txt"
    source.write_text("safe", encoding="utf-8")
    process = _StartFailureProcess(stops_on_terminate=True)
    context = _TrackedContext(process)
    monkeypatch.setattr(
        supervisor.multiprocessing, "get_context", lambda _method: context
    )

    with pytest.raises(OSError, match="process creation failed"):
        extract_text_isolated(
            source,
            "text/plain",
            timeout_seconds=5,
            heartbeat_interval_seconds=1,
        )

    assert context.receive.closed is True
    assert context.send.closed is True

