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
  --rows 1000 --modes sparse,dense,no-match --repetitions 2
```

The default matrix is 10k / 100k / 500k rows, sparse / dense / no-match target IDs,
three repetitions, and batches of 200. Reduce the matrix on constrained machines.
The 500k case is optional and may take several minutes.

## Reported measures

- Non-null snapshot count and actual matching-row count.
- Rows scanned/locked per run (the current query locks every non-null snapshot).
- Average and p95 JSON-array length.
- Scan latency p50/p95 across repetitions.
- Peak Python memory observed during the scan.
- A concurrent lock-wait probe against an unrelated synthetic row while the full scan
  holds its row locks.

The output includes PostgreSQL version, seed, batch size, and UTC timestamp. Save the
JSON report together with the exact commit SHA and runner hardware/CPU/RAM. Compare
results only on comparable environments. This benchmark does not set an SLO and does
not justify a schema/index change by itself.

## Limitations

This isolates the query/locking shape using a generic SQLAlchemy `JSON` column, matching
the model's declared type. It does not reproduce application-level workspace/assistant
locks, production concurrency, network latency, or all PostgreSQL storage characteristics.
Use it to establish an initial baseline, then validate any candidate optimization with
the same dataset and workload before changing implementation.
