#!/usr/bin/env python3
"""Opt-in benchmark for the current assistant-version retention scan.

Creates a uniquely named synthetic schema only. Refuses non-local/non-test database
URLs before connecting. No application table is read or modified.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import random
import statistics
import threading
import time
import tracemalloc
import uuid
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, JSON, MetaData, Table, create_engine, select, text
from sqlalchemy.engine import make_url

DEFAULT_URL = "postgresql://postgres:postgres@localhost:5432/ai_backend_test"
TARGET_FILE_ID = -1


def local_test_url() -> str:
    value = os.getenv("TEST_DATABASE_URL", DEFAULT_URL)
    parsed = make_url(value)
    if (
        parsed.drivername.split("+", 1)[0] != "postgresql"
        or parsed.host not in {"localhost", "127.0.0.1"}
        or parsed.port != 5432
        or parsed.database != "ai_backend_test"
        or parsed.query
    ):
        raise SystemExit(
            "Refusing database URL: only localhost:5432/ai_backend_test "
            "without query parameters is allowed."
        )
    return value


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * fraction + 0.5)))
    return ordered[index]


def synthetic_batches(count: int, mode: str, seed: int, batch_size: int, array_ratio: float):
    rng = random.Random(seed)
    next_id = 1
    while next_id <= count:
        batch = []
        for _ in range(min(batch_size, count - next_id + 1)):
            if rng.random() > array_ratio:
                ids = None
            else:
                length = rng.randint(1, 8)
                ids = [rng.randint(1, max(10, count // 10)) for _ in range(length)]
                if mode == "dense" or (mode == "sparse" and rng.random() < 0.01):
                    ids[rng.randrange(length)] = TARGET_FILE_ID
            batch.append({"id": next_id, "knowledge_file_ids": ids})
            next_id += 1
        yield batch


def run_scan(engine, table: Table, batch_size: int):
    statement = (
        select(table.c.id, table.c.knowledge_file_ids)
        .where(table.c.knowledge_file_ids.is_not(None))
        .order_by(table.c.id.asc())
        .with_for_update()
        .execution_options(yield_per=batch_size)
    )
    scanned = matched = 0
    tracemalloc.start()
    started = time.perf_counter()
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                result = connection.execution_options(stream_results=True).execute(statement)
                for row in result:
                    scanned += 1
                    if isinstance(row.knowledge_file_ids, list) and TARGET_FILE_ID in row.knowledge_file_ids:
                        matched += 1
                result.close()
            finally:
                transaction.rollback()
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return scanned, matched, elapsed_ms, peak_bytes


def measure_unrelated_lock_wait(engine, table: Table, row_id: int, batch_size: int) -> float:
    """Measure a concurrent lock request on a synthetic row outside the target set."""
    query_started = threading.Event()
    waiter_pid: list[int] = []

    def waiter() -> float:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text("SET LOCAL lock_timeout = '8s'"))
                waiter_pid.append(connection.execute(text("SELECT pg_backend_pid()")).scalar_one())
                query_started.set()
                started = time.perf_counter()
                connection.execute(
                    select(table.c.id).where(table.c.id == row_id).with_for_update()
                ).first()
                elapsed = (time.perf_counter() - started) * 1000
                transaction.rollback()
                return elapsed
            except Exception:
                transaction.rollback()
                raise

    with engine.connect() as locker:
        transaction = locker.begin()
        try:
            result = locker.execution_options(stream_results=True).execute(
                select(table.c.id, table.c.knowledge_file_ids)
                .where(table.c.knowledge_file_ids.is_not(None))
                .order_by(table.c.id.asc())
                .with_for_update()
                .execution_options(yield_per=batch_size)
            )
            for _ in result:
                pass
            result.close()
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(waiter)
                if not query_started.wait(timeout=3):
                    raise RuntimeError("Lock-wait probe did not start")
                deadline = time.monotonic() + 5
                observed_lock_wait = False
                while time.monotonic() < deadline:
                    wait_event = locker.execute(
                        text(
                            "SELECT wait_event_type FROM pg_stat_activity "
                            "WHERE pid = :pid"
                        ),
                        {"pid": waiter_pid[0]},
                    ).scalar_one_or_none()
                    if wait_event == "Lock":
                        observed_lock_wait = True
                        break
                    if future.done():
                        break
                    time.sleep(0.01)
                transaction.rollback()
                elapsed = future.result(timeout=10)
                if not observed_lock_wait:
                    raise RuntimeError(
                        "PostgreSQL did not report the unrelated-row probe waiting on a lock"
                    )
                return elapsed
        finally:
            if transaction.is_active:
                transaction.rollback()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", default="10000,100000,500000")
    parser.add_argument("--modes", default="sparse,dense,no-match")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20261119)
    parser.add_argument("--array-ratio", "--non-null-ratio", dest="array_ratio", type=float, default=1.0,
                        help="Fraction of rows containing JSON arrays; remaining values are JSON null.")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    row_counts = [int(value) for value in args.rows.split(",")]
    modes = [value.strip() for value in args.modes.split(",")]
    if not row_counts or any(value < 1 or value > 500_000 for value in row_counts):
        raise SystemExit("--rows values must be between 1 and 500000")
    if not modes or any(mode not in {"sparse", "dense", "no-match"} for mode in modes):
        raise SystemExit("--modes accepts sparse,dense,no-match")
    if not 1 <= args.repetitions <= 20 or args.batch_size < 1:
        raise SystemExit("--repetitions must be 1..20 and --batch-size must be positive")
    if not 0 < args.array_ratio <= 1:
        raise SystemExit("--non-null-ratio must be greater than 0 and at most 1")

    engine = create_engine(local_test_url(), pool_size=3, max_overflow=0, pool_pre_ping=True)
    schema = "retention_bench_" + uuid.uuid4().hex
    metadata = MetaData(schema=schema)
    table = Table(
        "assistant_versions_synthetic",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("knowledge_file_ids", JSON, nullable=True),
    )
    results = []
    postgres_version = None

    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            metadata.create_all(connection)
            postgres_version = connection.execute(text("SHOW server_version")).scalar_one()

        for mode in modes:
            for count in row_counts:
                with engine.begin() as connection:
                    for batch in synthetic_batches(
                        count, "sparse" if mode == "no-match" else mode,
                        args.seed + count, args.batch_size, args.array_ratio,
                    ):
                        if mode == "no-match":
                            for item in batch:
                                if item["knowledge_file_ids"] is not None:
                                    item["knowledge_file_ids"] = [
                                        value for value in item["knowledge_file_ids"]
                                        if value != TARGET_FILE_ID
                                    ]
                        # Reserve the final row as a non-null, guaranteed non-matching lock probe.
                        if batch and batch[-1]["id"] == count:
                            batch[-1]["knowledge_file_ids"] = [count + 10]
                        connection.execute(table.insert(), batch)

                lengths = []
                expected_matches = 0
                with engine.connect() as connection:
                    stats = connection.execute(
                        select(table.c.knowledge_file_ids).order_by(table.c.id.asc())
                    )
                    for (ids,) in stats:
                        if ids is None:
                            continue
                        lengths.append(len(ids))
                        if TARGET_FILE_ID in ids:
                            expected_matches += 1
                    stats.close()

                durations = []
                peaks = []
                scanned_total = matched_total = 0
                for _ in range(args.repetitions):
                    scanned, matched, elapsed, peak = run_scan(engine, table, args.batch_size)
                    scanned_total += scanned
                    matched_total += matched
                    durations.append(elapsed)
                    peaks.append(peak)

                lock_wait_ms = measure_unrelated_lock_wait(
                    engine, table, count, args.batch_size
                )
                results.append({
                    "rows": count,
                    "mode": mode,
                    "array_snapshot_rows": len(lengths),
                    "json_null_rows": count - len(lengths),
                    "array_ratio_requested": args.array_ratio,
                    "expected_matches": expected_matches,
                    "scanned_rows_per_run": scanned_total // args.repetitions,
                    "matched_rows_per_run": matched_total // args.repetitions,
                    "array_length_avg": round(statistics.mean(lengths), 3),
                    "array_length_p95": percentile([float(x) for x in lengths], 0.95),
                    "scan_ms_p50": round(percentile(durations, 0.50), 3),
                    "scan_ms_p95": round(percentile(durations, 0.95), 3),
                    "scan_ms_samples": [round(value, 3) for value in durations],
                    "peak_python_memory_bytes_max": max(peaks),
                    "unrelated_row_lock_wait_ms": round(lock_wait_ms, 3),
                })
                with engine.begin() as connection:
                    # Avoid accumulating dead tuples between scenarios.
                    connection.exec_driver_sql(
                        f'TRUNCATE TABLE "{schema}".assistant_versions_synthetic'
                    )

    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        engine.dispose()

    report = {
        "benchmark": "assistant-version-retention-full-scan",
        "algorithm": (
            "SELECT id, knowledge_file_ids WHERE knowledge_file_ids IS NOT NULL "
            "ORDER BY id FOR UPDATE; stream rows and filter target IDs in Python"
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "commit_sha": os.getenv("GITHUB_SHA") or os.getenv("RETENTION_BENCH_COMMIT_SHA"),
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": multiprocessing.cpu_count(),
        },
        "database": "disposable local ai_backend_test only",
        "postgresql_version": postgres_version,
        "seed": args.seed,
        "repetitions": args.repetitions,
        "batch_size": args.batch_size,
        "non_null_ratio_requested": args.array_ratio,
        "results": results,
        "notes": [
            "Synthetic isolated schema only; no application tables are read or changed.",
            "Every scanned SQL-non-NULL row is locked, including JSON null values and snapshots unrelated to the target file.",
            "SQLAlchemy JSON defaults to none_as_null=False: Python None is stored as JSON null, which still passes SQL IS NOT NULL.",
            "Lock-wait probe requests a concurrent lock on an unrelated synthetic row.",
            "No performance SLO is asserted; record runner hardware and commit SHA with results.",
        ],
    }
    rendered = json.dumps(report, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
    print(rendered)


if __name__ == "__main__":
    main()
