# Assistant-version retention benchmark

This is an **opt-in diagnostic**, not part of the normal test suite and not a CI timing gate.
It measures the current retention strategy: scan every non-null `knowledge_file_ids`
snapshot in ID order, acquire row locks, stream the rows, and filter target IDs in Python.

## Safety boundary

The script refuses to connect unless `TEST_DATABASE_URL` resolves to PostgreSQL on
`localhost` or `127.0.0.1`, port `5432`, database `ai_backend_test`, with no URL
query parameters. It creates one random `retention_bench_<uuid>` schema, uses only a
synthetic table inside that schema, and drops that schema on exit. It does not access
application tables. Do not weaken this guard or point it at Render, Supabase, staging,
or production.

## Run

From `ai-backend/`, after starting the disposable local PostgreSQL test service and
installing `requirements.txt`:

```bash
python scripts/benchmark_project_file_retention.py
```

A small smoke run:

```bash
python scripts/benchmark_project_file_retention.py \
  --rows 1000 --modes sparse,dense,no-match --non-null-ratio 0.5 --repetitions 2
```

The default matrix is 10k / 100k / 500k rows, sparse / dense / no-match target IDs,
100% non-null snapshots, three repetitions, and batches of 200. Set
`--non-null-ratio 0.5` to model a 50% non-null snapshot population. Reduce the matrix
on constrained machines.
The 500k case is optional and may take several minutes.

## Reported measures

- Requested and observed non-null snapshot count, plus actual matching-row count.
- Rows scanned/locked per run (the current query locks every non-null snapshot).
- Average and p95 JSON-array length.
- Scan latency p50/p95 across repetitions, plus every individual scan duration (`scan_ms_samples`) so small-sample results remain inspectable.
- Peak Python memory observed during the scan.
- A concurrent lock-wait probe against an unrelated synthetic row while the full scan
  holds its row locks; the probe waits until PostgreSQL reports the waiter in
  `pg_stat_activity.wait_event_type = 'Lock'` before releasing the scan transaction.

The output includes PostgreSQL version, seed, batch size, UTC timestamp, Python/runtime
platform, machine architecture, and CPU count. Set `RETENTION_BENCH_COMMIT_SHA` to the
benchmark commit before running when `GITHUB_SHA` is not already available. Save the JSON
report together with the exact commit SHA and runner hardware/CPU/RAM. Compare
results only on comparable environments. With the default three repetitions, p95 is a
coarse descriptive quantile (effectively near the upper observed sample), not a statistically
reliable tail-latency estimate; inspect `scan_ms_samples` and increase repetitions for
exploratory comparisons when the machine can support it. This benchmark does not set an SLO
and does not justify a schema/index change by itself.

## Limitations

This isolates the query/locking shape using a generic SQLAlchemy `JSON` column, matching
the model's declared type. It does not reproduce application-level workspace/assistant
locks, production concurrency, network latency, or all PostgreSQL storage characteristics.
Use it to establish an initial baseline, then validate any candidate optimization with
the same dataset and workload before changing implementation.
