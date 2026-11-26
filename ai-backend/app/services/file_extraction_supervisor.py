"""Spawn-based parser isolation primitives.

This module is deliberately not wired into the upload worker. It bounds one
parser child, installs Linux parent-death containment before parsing, and
verifies child exit before returning. Unsupported platforms fail closed.
"""
from __future__ import annotations

import ctypes
import json
import multiprocessing
import os
import signal
import sys
import time
from pathlib import Path
from typing import Callable

from app.services.file_text_extractor import (
    DEFAULT_MAX_CHARS,
    FileTextExtractionError,
    extract_text,
)
from app.services.storage import PreserveMaterializedFile


MAX_PARSER_RESULT_BYTES = 128 * 1024
DEFAULT_PARSER_TIMEOUT_SECONDS = 60.0
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 2.0
TERMINATE_GRACE_SECONDS = 1.0


class ExtractionSupervisorError(RuntimeError):
    """A bounded parser execution failed without exposing parser internals."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _configure_parent_death_signal(expected_parent_pid: int) -> None:
    """Require Linux parent-death SIGKILL and close the setup race.

    PR_SET_PDEATHSIG is Linux-specific. Unsupported platforms fail closed:
    the child must never begin parsing without this containment guarantee.
    """
    if sys.platform != "linux":
        raise RuntimeError("parent_death_containment_unavailable")

    libc = ctypes.CDLL(None, use_errno=True)
    pr_set_pdeathsig = 1
    if libc.prctl(pr_set_pdeathsig, signal.SIGKILL, 0, 0, 0) != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, "unable to configure parent-death signal")

    # If the parent died before prctl() was installed, the signal would have
    # been missed. Detect reparenting after installation and kill this child.
    if os.getppid() != expected_parent_pid:
        os.kill(os.getpid(), signal.SIGKILL)


def _parser_child(
    source_path: str,
    content_type: str,
    max_chars: int,
    expected_parent_pid: int,
    send_connection,
) -> None:
    """Spawn target: receives only a path, metadata, parent PID, and one pipe."""
    try:
        _configure_parent_death_signal(expected_parent_pid)
        result = extract_text(source_path, content_type, max_chars=max_chars)
        payload = json.dumps(
            {"ok": True, "text": result},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except Exception:
        payload = b'{"ok":false,"error":"document_extraction_invalid"}'

    try:
        send_connection.send_bytes(payload)
    finally:
        send_connection.close()


def _stop_child(process) -> bool:
    """Terminate, then kill if needed; return true only with verified exit."""
    try:
        if process.is_alive():
            process.terminate()
        process.join(TERMINATE_GRACE_SECONDS)
        if process.is_alive():
            process.kill()
            process.join(TERMINATE_GRACE_SECONDS)
        return not process.is_alive() and process.exitcode is not None
    except (AssertionError, OSError, ValueError):
        return False


def extract_text_isolated(
    source_path: str | Path,
    content_type: str,
    *,
    heartbeat: Callable[[], bool] | None = None,
    max_chars: int = DEFAULT_MAX_CHARS,
    timeout_seconds: float = DEFAULT_PARSER_TIMEOUT_SECONDS,
    heartbeat_interval_seconds: float = DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
) -> str | None:
    """Extract in a spawned child, returning only a bounded JSON result.

    If child termination cannot be proven, preserve the materialized source
    and raise. A caller must not persist, reclaim, or delete after that signal.
    Linux PR_SET_PDEATHSIG containment is installed in the child before parsing;
    unsupported platforms fail closed. The caller remains responsible for a
    hard job deadline supplied by its external runtime.
    """
    path = Path(source_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    if not isinstance(content_type, str) or not content_type:
        raise ExtractionSupervisorError("invalid_content_type")
    if not isinstance(max_chars, int) or max_chars < 1 or max_chars > DEFAULT_MAX_CHARS:
        raise ExtractionSupervisorError("invalid_output_limit")
    if (
        not isinstance(timeout_seconds, (int, float))
        or timeout_seconds <= 0
        or timeout_seconds > 300
        or not isinstance(heartbeat_interval_seconds, (int, float))
        or heartbeat_interval_seconds <= 0
        or heartbeat_interval_seconds >= timeout_seconds
    ):
        raise ExtractionSupervisorError("invalid_supervisor_timing")

    context = multiprocessing.get_context("spawn")
    receive_connection, send_connection = context.Pipe(duplex=False)
    process = context.Process(
        target=_parser_child,
        args=(str(path), content_type, max_chars, os.getpid(), send_connection),
        daemon=True,
        name="ai-chat-file-parser",
    )
    started = False
    try:
        process.start()
        started = True
        send_connection.close()
        deadline = time.monotonic() + float(timeout_seconds)
        next_heartbeat = time.monotonic() + float(heartbeat_interval_seconds)

        while True:
            if receive_connection.poll(0.05):
                try:
                    payload = receive_connection.recv_bytes(MAX_PARSER_RESULT_BYTES)
                except (EOFError, OSError) as exc:
                    raise ExtractionSupervisorError("parser_result_invalid") from exc
                process.join(TERMINATE_GRACE_SECONDS)
                if process.is_alive() or process.exitcode is None:
                    if not _stop_child(process):
                        raise PreserveMaterializedFile(path)
                    raise ExtractionSupervisorError("parser_exit_unverified")
                try:
                    decoded = json.loads(payload.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ExtractionSupervisorError("parser_result_invalid") from exc
                if not isinstance(decoded, dict) or decoded.get("ok") is not True:
                    raise FileTextExtractionError("document extraction failed")
                result = decoded.get("text")
                if result is not None and not isinstance(result, str):
                    raise ExtractionSupervisorError("parser_result_invalid")
                return result

            if not process.is_alive():
                process.join(TERMINATE_GRACE_SECONDS)
                raise ExtractionSupervisorError("parser_exited_without_result")

            now = time.monotonic()
            if now >= deadline:
                if not _stop_child(process):
                    raise PreserveMaterializedFile(path)
                raise ExtractionSupervisorError("parser_timeout")

            if heartbeat is not None and now >= next_heartbeat:
                try:
                    renewed = heartbeat()
                except Exception as exc:
                    if not _stop_child(process):
                        raise PreserveMaterializedFile(path) from exc
                    raise ExtractionSupervisorError("heartbeat_failed") from exc
                if renewed is not True:
                    if not _stop_child(process):
                        raise PreserveMaterializedFile(path)
                    raise ExtractionSupervisorError("heartbeat_lost")
                next_heartbeat = now + float(heartbeat_interval_seconds)
    finally:
        receive_connection.close()
        if not started:
            send_connection.close()
        if started and process.is_alive():
            if not _stop_child(process):
                # The source must remain available if the child may still read it.
                raise PreserveMaterializedFile(path)
        if started:
            process.close()
