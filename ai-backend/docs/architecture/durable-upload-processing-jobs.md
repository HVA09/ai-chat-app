# Durable Upload Processing Jobs — Architecture and Rollout

**Status:** implementation in progress in PR #767; dispatcher helper and tests added, not scheduled or enabled in production  
**Scope:** AI Chat App backend upload extraction, RAG indexing, and safe recovery  
**Non-goals:** enabling destructive reconciliation, changing production infrastructure, or changing current API behavior in this document

## 1. Executive decision

Use the existing PostgreSQL database as the source of truth for upload-processing state. Reuse the existing Celery integration only as a delivery/execution mechanism. Treat Redis messages as at-least-once notifications, never as the durable job record.

The upload lease remains the ownership/fencing record for the managed object. Introduce a durable processing-job record (which also acts as the transactional outbox) so the upload transaction can commit both the lease transition and the work that must eventually run. A periodic dispatcher republishes eligible jobs until a worker claims them. Duplicate messages must be harmless.

Do not enable a cleanup reconciler, age-based deletion, or lease-expiry deletion as part of this change. A timeout or expired heartbeat is not proof that a worker has stopped.

## 2. Verified current-state constraints

The current branch already has:

- `UploadLease` with an immutable managed `object_key`, optional `staging_key`, status, monotonically increasing `generation`, owner-token hash, heartbeat/expiry timestamps, and optional attachment ID.
- Cleanup-intent persistence with lease identity and generation checks.
- Celery configured with Redis broker/result backend and existing email, scheduled-task, agent-job, and webhook tasks.
- Render's current backend startup script can embed a single-concurrency Celery worker and Beat in the web process.
- The upload route still performs extraction in the HTTP request. RAG embedding generation and index persistence are also invoked synchronously from that request path.
- Render's web filesystem is not a durable cross-service work volume. Managed uploads must be read from configured object storage by a future worker; a local path must not be assumed shared or persistent.

Consequently, the existing `queued` lease state is not proof that a Celery message exists, and adding a task wrapper around the current synchronous functions would not by itself provide durable processing.

## 3. Target data model

Add an `upload_processing_jobs` table through a new Alembic migration. Keep the schema deliberately small and database-portable where practical.

| Field | Purpose |
|---|---|
| `id` | UUID primary key |
| `lease_id` | FK to `upload_leases.id`; retain referential integrity |
| `stage` | `extract` or `index` |
| `stage_revision` | Explicit revision for deliberate reprocessing |
| `status` | `pending_dispatch`, `queued`, `processing`, `retry_wait`, `succeeded`, `failed_terminal`, `cancelled` |
| `generation` | Monotonic fencing generation for this job claim |
| `owner_token_hash` | Hash of random claim token; never persist the raw token |
| `attempt_count` | Bounded delivery/processing attempts |
| `available_at` | Earliest eligible retry/dispatch time |
| `heartbeat_at`, `expires_at` | Observability and advisory liveness only |
| `started_at`, `completed_at` | Stage lifecycle timestamps |
| `last_error_code` | Safe, bounded error classification; no secrets or raw provider payloads |
| `created_at`, `updated_at` | Audit timestamps |

Required constraints/indexes:

- Unique idempotency key over `(lease_id, stage, stage_revision)`.
- Index eligible jobs by `(status, available_at, created_at)`.
- Index active jobs by `(lease_id, status)`.
- Foreign-key behavior must preserve recovery/audit metadata if a user is deleted. Do not cascade-delete the job or lease with the user.
- The attachment identity is resolved and revalidated at finalization; do not trust an attachment ID carried only in a broker message.

The job row doubles as the outbox. This avoids a dual-write between a job table and a separate outbox table. If later event fan-out requires a general outbox, that should be a separate design.

## 4. Upload and processing lifecycle

### A. Ingress (HTTP request)

1. Authenticate and validate request metadata.
2. Lock the user row and create the upload lease before writing managed bytes, preserving the established User → Lease lock order.
3. Stream the body to a bounded temporary file and durable object storage. Heartbeat the ingress lease during awaited body reads.
4. Once the storage writer has returned, create the initial extraction job and transition the lease to its accepted/queued state in one database transaction. The unique job key makes request retries idempotent.
5. Commit the transaction. A best-effort immediate dispatch may reduce latency, but the request must not depend on Redis availability for durability.
6. Return a truthful processing state. API/UI compatibility must be handled explicitly: do not claim extracted text or completed indexing before those stages succeed.

The HTTP request must not hold a User row lock while performing extraction or waiting on an embedding provider.

### B. Outbox dispatch

The implemented bounded dispatcher scans due `pending_dispatch` / `retry_wait` jobs and stale `queued` jobs, locks each row with `FOR UPDATE SKIP LOCKED`, and publishes only the job ID. It then sets the row to `queued` and updates `updated_at` in the same caller-owned transaction. Workers may claim `pending_dispatch`, `retry_wait`, or `queued` rows under the same row lock. A worker receiving a fast message waits for the dispatch transaction, then sees the committed queued state. A dispatcher crash after broker acceptance can cause duplicate publication; worker claim fencing makes duplicate deliveries harmless. Stale queued rows are republished after a bounded interval so broker acknowledgement loss does not strand the job.

- Publish failure leaves the durable job eligible for retry with bounded backoff.
- Publish success is not job completion. The worker still has to claim the database row.
- A crash between publish and recording dispatch may publish a duplicate; this is expected and must be safe.
- The dispatcher never deletes objects and never infers that a worker has stopped.

A Beat-triggered dispatcher is acceptable only as a trigger. The database row remains authoritative, and an independently supervised process must ensure dispatch resumes after Beat or broker interruption.

### C. Worker claim and fencing

A worker receives a job ID, opens a short DB transaction, locks/conditionally updates the job, and claims it only if:

- the job is in an eligible state and is due;
- the associated lease is in the expected state and generation;
- the owner user still exists and is authorized for this operation;
- the attempt budget has not been exhausted.

Claim increments the job generation and stores only a hash of a fresh random owner token. Every heartbeat, state transition, and result commit must compare the job ID, generation, and token hash. A stale worker must be unable to commit even if it resumes after a newer generation has claimed the job.

Broker messages are at-least-once. Duplicate deliveries that cannot claim the current generation must exit without side effects.

### D. Extraction stage

- Fetch source bytes from managed object storage into a per-task isolated temporary directory.
- Enforce explicit byte, archive expansion, page/row/paragraph, output-character, and wall-clock limits.
- Run parsing in a killable process boundary, not a thread whose timeout merely stops waiting.
- Do not hold a user-row lock while parsing.
- After parsing, open a short transaction, lock User → Lease → Job in the documented order, revalidate user existence and all fencing generations, and persist extracted text plus the next-stage job atomically.
- If the user has been deleted or the generation is stale, do not create/update an attachment or schedule indexing. Leave cleanup to the fenced recovery protocol after worker termination is established.

Extraction output must be bounded before it is materialized in memory. Existing parser paths that call `Path.read_bytes()` before slicing or traverse all DOCX paragraphs/tables before applying an output limit need separate bounded-reader work.

### E. Index stage

- Load the committed attachment and its extracted-text fingerprint from the database.
- Generate embeddings outside a DB write transaction and outside a user-row lock.
- Persist the complete replacement index atomically only after rechecking attachment ownership, text fingerprint, job generation, and current user/lease state.
- Use the existing `prepare_file_index` / `persist_file_index` split in `rag.py` as the starting point.
- A provider failure must not delete or partially replace a previously valid index.
- On retry, reusing the same `(lease_id, stage, stage_revision)` must not create duplicate chunks or multiple successful terminal outcomes.

### F. Completion

Mark the job stage succeeded only in the same transaction that persists its durable result. Mark the lease/attachment processing state consistently with the completed stages. A successful extraction is not equivalent to successful indexing; expose the distinction rather than overloading one status.

## 5. Worker runtime and termination proof

The production target should be a separately supervised Render Background Worker using the same immutable backend image and environment contract as the web service. It must use the same durable database and object-storage bucket, but it must not depend on a shared local filesystem.

Do not treat the current embedded worker in the web process as the final production topology. It couples API availability, Beat, and worker lifecycle and gives no independent worker health boundary.

Celery configuration to evaluate and test explicitly:

- prefork pool and bounded concurrency;
- task soft and hard time limits derived from measured parser/provider budgets;
- late acknowledgement and reject-on-worker-lost semantics where appropriate;
- worker prefetch bounded to avoid claiming work far ahead of available execution slots;
- bounded retries with exponential backoff and jitter;
- task result expiry is not a substitute for job-state retention;
- graceful shutdown followed by a bounded hard-stop policy.

A hard time limit is necessary but not sufficient. Tests and runtime evidence must show that the task child process is terminated and reaped, that it cannot continue reading/writing after fencing, and that redelivery cannot overlap with an old live execution. If the platform cannot establish this, leave the job in an explicit uncertain/recovery state and do not authorize destructive cleanup.

## 6. Account deletion and lock ordering

Preserve the existing lock-order contract:

1. User row
2. UploadLease row
3. UploadProcessingJob row
4. FileAttachment / workspace rows as required by the operation

Account deletion must coordinate with active leases and jobs. It must prevent new claims for the deleted user, fence active generations, and retain the minimal lease/job recovery metadata needed to handle stored objects. A worker that finishes after deletion must fail its user-existence/fencing check and must not recreate user-owned records.

Never hold a user-row lock across object-storage I/O, document parsing, or embedding-provider requests. Use short transactions around authorization and durable state transitions.

## 7. Retry and terminal-state policy

- Retry only classified transient failures (broker unavailable, temporary storage read failure, provider timeout/rate limit, transient DB disconnect).
- Do not retry invalid file types, archive-policy violations, unsupported formats, or deterministic parser failures without a code/configuration change.
- Use bounded exponential backoff with jitter and a finite attempt budget.
- Persist safe error codes and attempt timestamps; never log owner tokens, credentials, extracted contents, or raw provider payloads.
- Terminal failure remains visible and recoverable by an explicit user/admin action; it must not silently delete the source object.
- A duplicate task or repeated dispatcher pass must be idempotent.

## 8. Cleanup safety boundary

This design does **not** authorize automatic object deletion.

Cleanup may be considered only after all of the following are implemented and independently tested:

- A durable cleanup intent bound to immutable object key, lease ID, and generation.
- A verified terminal state for the exact worker execution, including child termination/reaping.
- A current database check proving no committed attachment references the object.
- A fenced lease transition to cleanup-pending that cannot be performed by an older generation.
- Account-deletion race coverage and explicit handling of user-row absence.
- Bounded retries/backoff, dry-run, bounded batches, safe logs/metrics, and persisted progress.
- Fail-closed behavior for DB errors, partial object listings, ambiguous metadata, stale generations, or uncertain worker liveness.

Lease expiry, missing heartbeat, Redis visibility timeout, request cancellation, or a coroutine/thread timeout is never sufficient deletion authority.

## 9. Required test matrix

All tests must use isolated test databases and fake/local object storage. No hosted database, Render service, production bucket, or real user data.

| Scenario | Required assertion |
|---|---|
| DB commit succeeds, broker publish fails | Job remains durable and is dispatched later |
| Publish succeeds, dispatcher crashes before recording | Duplicate delivery is harmless |
| Worker receives duplicate message | Only one current generation can claim |
| Worker dies before claim | Job remains dispatchable |
| Worker dies after claim | Redelivery cannot overlap an unproven live child |
| Hard task timeout | Child is terminated/reaped; no later writes occur |
| Old worker resumes after a newer claim | Fencing rejects heartbeat, result commit, and state transition |
| Extraction succeeds, index provider fails | Extracted source remains durable; index job retries safely |
| Index generation repeats | No duplicate chunks or partial replacement |
| Account deletion during extraction | No attachment/index resurrection; cleanup remains fenced |
| Account deletion during embedding | No chunk/audit write for deleted user |
| Object-storage read/list partial failure | No destructive action |
| DB unavailable during dispatch/recovery | Fail closed; no object deletion |
| Terminal deterministic parser error | No infinite retry; source object preserved |
| Retry budget exhausted | Visible terminal state; no automatic deletion |
| Legacy attachment with null object_key | Existing attachment remains preserved |

Use PostgreSQL integration tests for row locks, conditional updates, unique constraints, and account-deletion races. SQLite-only tests are not sufficient evidence for those semantics.

## 10. Safe implementation sequence

1. **Schema and service layer:** add the job model/migration, state-transition service, idempotency constraints, and unit/PostgreSQL tests. No worker is enabled yet.
2. **Outbox dispatcher:** add bounded dispatch and duplicate-publication tests. Keep it disabled in production until explicitly configured.
3. **Extraction worker:** add storage-backed input, isolated bounded parsing, child-termination tests, and atomic extraction completion.
4. **Index worker:** use the existing prepare/persist RAG split with generation checks and idempotency tests.
5. **API/UI contract:** add truthful processing status and preserve existing upload/list/download behavior; test mobile and web clients.
6. **Worker deployment definition:** add a separate Render worker definition as a reviewed configuration change only. Do not apply it or change production environment variables in this implementation branch.
7. **Operational verification:** staging-only isolated test bucket/database, worker-loss drills, metrics, bounded retries, and rollback plan.
8. **Cleanup design review:** only after the preceding evidence exists; cleanup remains disabled until independent review and destructive-path acceptance tests pass.

## 10A. Enforceable parser supervision — implementation gate

The current upload worker still calls `extract_text(...)` in-process; the standalone supervisor primitive is **not wired into that worker**. Its 300-second job lease is **not** a parser deadline, and a failed post-parse heartbeat only prevents persistence; it does not stop a parser that is still running.

The standalone supervisor now installs Linux `PR_SET_PDEATHSIG(SIGKILL)` in the spawned parser child before parsing and checks the expected parent PID after installation to close the setup race. Unsupported platforms and a failed `prctl` setup fail closed before parser execution. A Linux process-level regression test terminates the supervising parent and verifies the child is no longer executable. This guarantee is scoped to the direct parser child only; it does not establish a hard overall job lifetime, worker-runtime supervision, descendant-process containment, credential isolation, or the complete no-persist/no-reclaim/no-delete matrix. A child or native parser library may create descendants that are not automatically covered by the direct child's parent-death signal; process-tree containment requires a separate OS-level mechanism and regression test. Do not wire this primitive into the worker or change the upload route until the remaining gates are implemented and verified.

### Required parent/child contract

1. Keep object materialization, job ownership, heartbeats, and all database access in the supervised parent. Pass only a local read-only source path, validated MIME type, and bounded parser options as explicit child arguments. **This is not credential isolation:** a spawned child inherits the parent process environment and OS identity/permissions unless a separate launcher explicitly sanitizes them. The current implementation does not provide a reduced-privilege sandbox; do not claim that omitting credentials from function arguments prevents access to inherited environment secrets or service-readable files. Before parsing untrusted documents in a production worker, either introduce and test a separately sandboxed execution identity/environment with restricted filesystem and network access, or document and accept that parser code runs with the worker service account's inherited privileges. The child must never receive owner tokens or authority to update job state as explicit inputs.
2. Launch the parser in a dedicated spawned process (not a thread and not a fork of a live SQLAlchemy/Celery process). Give it a private per-job temporary directory and enforce input-byte, archive-expansion, page/row/paragraph, output-character, and wall-clock budgets before returning a result.
3. The parent waits only until the configured monotonic deadline. On timeout or cancellation, request graceful termination, wait for a short bounded grace interval, then force-kill the child if it remains alive.
4. After force-kill, call join/wait and verify the child is no longer alive and has an exit status. A timeout, terminate request, kill request, or elapsed lease alone is **not** termination proof.
5. If the parent cannot confirm child exit/reaping, it must fail closed: do not persist extraction output, do not mark the job safely stopped, do not reclaim its generation, and do not delete the source object or temporary directory. Keep durable state for operator investigation.
6. Only after child exit is confirmed may the parent discard partial output, close IPC handles, and remove the per-job temporary directory. The normal result path still requires a fresh generation/token fence before persistence.
7. Heartbeat renewal must run in the parent using short independent DB transactions while the child parses. A failed heartbeat cancels the child and prohibits all later result writes; the parent must still confirm child termination before reporting that execution has stopped.
8. The child result channel must be bounded and validated. Do not allow unbounded pickle payloads, arbitrary object deserialization, or parser exceptions containing document text/secrets to enter durable job error fields.

### Required tests before broker/runtime wiring

- A parser that completes before the deadline returns a bounded result and is reaped.
- A parser that exceeds the deadline is terminated, joined, and proven not alive before the parent returns.
- A parser that ignores graceful termination is force-killed and reaped by a real process-level test (not only a fake process).
- A simulated failure to confirm child exit fails closed and does not persist, reclaim, or delete anything.
- Heartbeat loss during parsing cancels the child; a late child result cannot be persisted.
- Parent crash / worker loss during parsing leaves durable state untouched; no expiry-based cleanup or automatic reclaim follows.
- Child IPC failure, malformed result, oversized result, and parser exception are sanitized and bounded.
- Account deletion racing with extraction cannot permit a child result to recreate or mutate attachment/index state.

A process supervisor can prove only that its parser child has exited; it does not prove that unrelated external provider or storage operations have stopped. Keep parser execution separate from embedding/provider calls and object-storage mutation. The existing worker must remain unregistered and the synchronous route unchanged until these tests and the later integration review pass.

## 11. Explicit non-changes for this PR step

- No production deployment, environment-variable change, migration against hosted DB, or object-storage operation.
- No bucket-wide scan, age-only deletion, lease-expiry deletion, or active cleanup reconciler.
- No automatic PR merge or bypass of branch protection/review requirements.
- No claim that this design document itself fixes the current synchronous request path.

**Acceptance for the next code change:** implement the isolated parser supervisor and its kill/reap, heartbeat-loss, bounded-output, and fail-closed tests without registering a Celery task or changing the HTTP upload route. Run the full backend suite and CodeQL on the exact commit. Broker wiring, index-worker implementation, API/UI state changes, and any deployment remain later separately reviewed stages.
