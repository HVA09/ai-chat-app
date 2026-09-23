# AI Platform Roadmap

This document is the canonical engineering roadmap for this project.

## Engineering rule
Every future feature, fix, refactor, dependency upgrade, and deployment change must be checked against this roadmap before implementation.

For every phase:
1. Define exact scope.
2. Implement in small, auditable PRs.
3. Run CI, tests, security checks, and deployment validation applicable to the change.
4. Verify the change does not duplicate previous work.
5. Update this roadmap/checklist when the phase or milestone is completed.
6. Report each completed stage before moving to the next major stage.

## Target architecture
Chat + Agents + RAG + Memory + Tools/MCP + Code Sandbox + API + Connectors + Background Jobs + Observability + Security + Billing.

## Phase A — Production Foundation
Status: IN PROGRESS

### A1 Render production health
- [ ] Configure Render backend health check to /health.
- [ ] Verify database-aware health.
- [ ] Add deployment smoke validation.

### A2 Background workers
- [ ] Run Celery Worker in production.
- [ ] Run Celery Beat in production.
- [ ] Verify background-job retries.

### A3 Data layer
- [ ] Move PostgreSQL from temporary/free production setup to an appropriate persistent plan.
- [ ] Configure production-grade Redis/persistence strategy.
- [ ] Review connection limits/pooling.

### A4 File storage
- [ ] Move uploads from local container storage to S3-compatible object storage.
- [ ] Add checksums/deduplication where appropriate.
- [ ] Add safe upload/download lifecycle.

### A5 Backups
- [ ] Keep automated DB backups.
- [ ] Copy backups off-host.
- [ ] Verify backup integrity.
- [ ] Perform and document a restore drill.

### A6 Real production deployment
- [ ] Real domain and HTTPS.
- [ ] Production CORS/FRONTEND_URL.
- [ ] Production payment and SMTP validation.
- [ ] End-to-end smoke test.

### A7 E2E coverage
- [ ] Add browser E2E tests for critical flows.
- [ ] Test desktop and mobile.
- [ ] Test auth, chat, files, RAG, permissions, notifications, and billing.

Phase A exit gate: production is persistent, observable, recoverable, and the critical user journey passes automated E2E/smoke checks.

## Phase B — Reliability and Operations
Status: PLANNED
- [ ] Structured logs and trace IDs.
- [ ] OpenTelemetry/tracing.
- [ ] Metrics dashboards and actionable alerts.
- [ ] AI provider timeout/retry/backoff/circuit breaker.
- [ ] Explicit background-job lifecycle.
- [ ] Separate DB migration job before API replicas.
- [ ] DB indexes/query optimization/connection pooling.
- [ ] Disaster-recovery documentation and restore drills.
- [ ] Operational runbooks.

Phase B exit gate: failures are detectable, diagnosable, retryable where safe, and recoverable.

## Phase C — Advanced AI/RAG
Status: PLANNED
- [ ] Model router with capability matrix.
- [ ] Provider fallback.
- [ ] Hybrid vector + keyword retrieval.
- [ ] Reranking.
- [ ] Citation/provenance system.
- [ ] Asynchronous indexing pipeline.
- [ ] Advanced chunking/document parsing.
- [ ] Advanced memory.
- [ ] AI token/cost controls.
- [ ] Evaluation framework.

Phase C exit gate: AI quality is measurable and RAG answers provide reliable provenance.

## Phase D — Agent Platform
Status: PLANNED
- [ ] Tool registry.
- [ ] Tool schemas and validation.
- [ ] Agent runtime/orchestration.
- [ ] MCP support.
- [ ] Connector/plugin architecture.
- [ ] Per-agent/per-workspace tool permissions.
- [ ] Long-running agent jobs.
- [ ] Scheduled agents.
- [ ] Human approval checkpoints for sensitive actions.
- [ ] Sandboxed code execution.

Security requirement: agents never receive unrestricted host/network/filesystem access.

Phase D exit gate: new capabilities can be added as tools/connectors without modifying the core chat architecture.

## Phase E — Platform/API
Status: PLANNED
- [ ] API keys.
- [ ] OAuth.
- [ ] Webhooks.
- [ ] API versioning.
- [ ] Idempotency.
- [ ] Cursor pagination.
- [ ] Developer dashboard.
- [ ] Python/JavaScript SDKs.
- [ ] Usage quotas.
- [ ] Cost controls.
- [ ] Agent/assistant configuration versioning.

Phase E exit gate: external applications can safely consume the platform through documented, versioned APIs.

## Security requirements across all phases
- Authentication/authorization remain deny-by-default.
- Enforce workspace/tenant isolation across API, DB, cache, object storage, RAG, workers, and WebSockets.
- Protect against prompt injection in untrusted content.
- Protect against SSRF in web/API tools.
- Scan uploads before privileged processing.
- Isolate secrets from agents/tools.
- Keep dependency/supply-chain checks enabled.
- Keep CodeQL and CI gates enabled.
- Never expose internal errors/secrets to users.
- New features must not bypass rate limits, quotas, audit logs, or permission checks.

## Multi-device change-control
GitHub main is the source of truth.
Before every new PR: sync against current main; search open/merged PRs for the intended feature/fix; avoid reimplementing already merged work; when two PRs solve the same problem, keep the current-main version and close the superseded one.

## Current baseline — 2026-09-23
- PR #201 merged: image RAG indexing fallback fix.
- PR #198 closed without merge: Tailwind 4 requires a separate migration.
- PR #200 closed as superseded by #201.
- CI and CodeQL are active.
- Render production exists but Phase A is not yet complete.

## Next milestone
Execute Phase A in this order:
1. Render health check.
2. Celery Worker + Beat.
3. Persistent production DB/Redis configuration.
4. Object Storage.
5. Off-host backups + restore drill.
6. Real domain/HTTPS.
7. E2E/smoke coverage.

Do not move to advanced Agent work until the Phase A exit gate is satisfied.
