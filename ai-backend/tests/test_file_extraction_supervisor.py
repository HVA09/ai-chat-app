"""Tests for the spawned parser supervisor primitive."""
import multiprocessing
import os
import sys
import time
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




def _parent_death_test_child(expected_parent_pid: int, ready_connection):
    from app.services.file_extraction_supervisor import _configure_parent_death_signal

    _configure_parent_death_signal(expected_parent_pid)
    ready_connection.send(os.getpid())
    ready_connection.close()
    while True:
        time.sleep(1)


def _parent_death_test_parent(result_connection):
    context = multiprocessing.get_context("spawn")
    receive_connection, send_connection = context.Pipe(duplex=False)
    child = context.Process(
        target=_parent_death_test_child,
        args=(os.getpid(), send_connection),
    )
    child.start()
    send_connection.close()
    child_pid = receive_connection.recv()
    receive_connection.close()
    result_connection.send(child_pid)
    result_connection.close()
    child.join()


@pytest.mark.skipif(sys.platform != "linux", reason="Linux PR_SET_PDEATHSIG only")
def test_parser_child_is_killed_when_supervising_parent_dies():
    context = multiprocessing.get_context("spawn")
    receive_connection, send_connection = context.Pipe(duplex=False)
    parent = context.Process(
        target=_parent_death_test_parent,
        args=(send_connection,),
    )
    parent.start()
    send_connection.close()

    child_pid = receive_connection.recv()
    receive_connection.close()
    parent.terminate()
    parent.join(timeout=5)
    assert not parent.is_alive()

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        proc_stat = Path(f"/proc/{child_pid}/stat")
        if not proc_stat.exists():
            return
        try:
            # A killed orphan may remain briefly as a zombie until reaped by
            # its new parent; state Z still proves it can no longer execute.
            state = proc_stat.read_text(encoding="ascii").split(")", 1)[1].split()[0]
        except (FileNotFoundError, IndexError):
            return
        if state == "Z":
            return
        time.sleep(0.05)

    pytest.fail("parser child remained executable after its parent was terminated")



def test_parent_death_signal_fails_closed_on_unsupported_platform(monkeypatch):
    from app.services import file_extraction_supervisor as supervisor

    monkeypatch.setattr(supervisor.sys, "platform", "darwin")
    with pytest.raises(RuntimeError, match="parent_death_containment_unavailable"):
        supervisor._configure_parent_death_signal(os.getpid())


def test_parent_death_signal_fails_closed_when_prctl_fails(monkeypatch):
    from app.services import file_extraction_supervisor as supervisor

    class _LibC:
        @staticmethod
        def prctl(*_args):
            return -1

    monkeypatch.setattr(supervisor.sys, "platform", "linux")
    monkeypatch.setattr(supervisor.ctypes, "CDLL", lambda *_args, **_kwargs: _LibC())
    monkeypatch.setattr(supervisor.ctypes, "get_errno", lambda: 1)
    with pytest.raises(OSError):
        supervisor._configure_parent_death_signal(os.getpid())


def test_parent_death_signal_detects_parent_pid_race(monkeypatch):
    from app.services import file_extraction_supervisor as supervisor

    class _LibC:
        @staticmethod
        def prctl(*_args):
            return 0

    killed = []
    monkeypatch.setattr(supervisor.sys, "platform", "linux")
    monkeypatch.setattr(supervisor.ctypes, "CDLL", lambda *_args, **_kwargs: _LibC())
    monkeypatch.setattr(supervisor.os, "getppid", lambda: 999999)
    monkeypatch.setattr(supervisor.os, "kill", lambda pid, sig: killed.append((pid, sig)))

    supervisor._configure_parent_death_signal(os.getpid())
    assert killed == [(os.getpid(), supervisor.signal.SIGKILL)]
