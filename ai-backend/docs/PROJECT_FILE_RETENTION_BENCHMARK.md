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
  --rows 1000 --modes sparse,dense,no-match --array-ratio 0.5 --repetitions 2
```

The script's local default matrix is 10k / 100k / 500k rows, sparse / dense / no-match target IDs,
100% array-valued snapshots, three repetitions, and batches of 200. Set
`--array-ratio 0.5` to generate arrays in about half the rows; the remaining Python `None` values are stored as JSON null, not SQL NULL. Reduce the matrix
on constrained machines.
The 500k case is optional and may take several minutes.

## Run on GitHub Actions (phone-friendly)

The repository also provides an isolated GitHub Actions workflow at
`.github/workflows/project-file-retention-benchmark.yml`. It starts a disposable
PostgreSQL service on the runner and exposes it only as
`localhost:5432/ai_backend_test`, so the script's local-only database guard remains
unchanged. The workflow installs only SQLAlchemy and psycopg, runs all three scenarios,
prints a compact summary, and uploads the JSON report as a 14-day artifact. It has
read-only repository permissions and uses no repository secrets or application services.

On pull requests that contain this workflow and target the retention benchmark base
branch, the workflow is scoped to the benchmark branch. After the workflow is merged
into the repository's default branch, it can also be started manually from
**Actions → Project file retention benchmark → Run workflow**. The current default is
10,000 rows, 3 repetitions, and a 0.5 array ratio; the 1,000-row smoke profile remains
available as a smaller option. Larger row counts are optional and should be used only
after reviewing the 10,000-row result.

The GitHub-hosted runner is a reproducible CI environment, not the user's laptop or
production infrastructure. Record its runner metadata and compare only runs on
comparable runner types.

## Reported measures

- Array-snapshot count, JSON-null count, and actual matching-row count.
- Rows scanned/locked per run (the current query locks every non-null snapshot).
- Average and p95 JSON-array length.
- Scan latency p50/p95 across repetitions, plus every individual scan duration (`scan_ms_samples`) so small-sample results remain inspectable.
- Peak Python memory observed during the scan.
- A concurrent lock-wait probe against an unrelated synthetic row while the full scan
  holds its row locks; the probe waits until PostgreSQL reports the waiter in
  `pg_stat_activity.wait_event_type = 'Lock'` before releasing the scan transaction.

The model uses SQLAlchemy `JSON` with its default `none_as_null=False`: Python `None` is stored as JSON null, not SQL NULL. Therefore JSON-null rows still satisfy the query's `IS NOT NULL` predicate and are scanned/locked. `array_snapshot_rows` counts list-valued snapshots; `json_null_rows` counts JSON null values. This matches the declared `AssistantVersion.knowledge_file_ids` JSON type. In this benchmark, the query therefore scans all generated rows, including JSON-null values; the array ratio changes match density, not the number of SQL rows selected.

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
