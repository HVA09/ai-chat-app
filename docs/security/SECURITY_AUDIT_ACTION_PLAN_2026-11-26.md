# Security Audit — Consolidated Tasks & Recommendations

**Repository:** `HVA09/ai-chat-app`  
**Scope:** AI Chat App only. This document must not be merged with Lumen, ERP, or other project plans.  
**Prepared:** 2026-11-26  
**Audit snapshot referenced in prior review notes:** `main` at `a40c50fce7dd1e531a8cbed5501206418dc66908`  
**Document status:** Consolidated remediation backlog; findings are not all runtime-verified.

## How to interpret this backlog

- Findings from rounds 251–256 are consolidated here. Repeated observations across rounds are represented once.
- Earlier references (including rounds 243 and 246) are cross-references to avoid duplicate tickets, not new findings.
- Severity is provisional: P1 = high priority security exposure; P2 = important hardening or integrity issue.
- "Source-reviewed" means identified in a prior static source review. It does not mean exploited, reproduced, or verified in production.
- Before implementation, re-check the current default-branch SHA and affected code. Close or downgrade an item if the code has changed or the finding cannot be reproduced.
- No production actions, migrations, secrets changes, or runtime tests were performed as part of this consolidation.

## P1 — High-priority remediation

### SEC-001 — Bind access tokens to revocable sessions
- **Area:** Authentication / session lifecycle
- **References:** Rounds 243, 246, 256
- **Previously reviewed paths:** `ai-backend/app/auth/routes.py`, `ai-backend/app/dependencies.py`, `ai-backend/app/auth/security.py`
- **Observation:** Access tokens were reported not to carry a session identifier/JTI linked to the session record. Revoking a refresh/session record may therefore leave an already-issued access token usable until expiry.
- **Tasks:**
  - Include a session identifier (and preferably a unique token identifier) in access tokens.
  - Validate that the session is active and belongs to the authenticated user.
  - Define a low-latency revocation strategy that does not create an uncontrolled database lookup on every request.
  - Add tests for single-session revocation, logout, account-wide revocation, and concurrent requests.
- **Acceptance:** A revoked session's access token is rejected within the documented revocation SLA; unrelated sessions remain valid.

### SEC-002 — Invalidate tokens on account disable and re-enable
- **Area:** Authentication / account lifecycle
- **Reference:** Round 256
- **Previously reviewed path:** `ai-backend/app/routers/admin.py`
- **Observation:** The review reported that changing `is_active` did not consistently increment `token_version`. A token blocked while the account is disabled could become usable again after reactivation if its version remains current.
- **Tasks:**
  - Increment the token/session generation on both disable and re-enable.
  - Revoke active sessions when disabling an account.
  - Ensure reactivation never restores previously issued credentials.
- **Acceptance:** Tokens issued before either state transition remain invalid after reactivation.

### SEC-003 — Protect first-admin bootstrap and admin role assignment
- **Area:** Identity / privileged access
- **Reference:** Round 256
- **Previously reviewed path:** `ai-backend/app/auth/routes.py`
- **Observation:** The review reported that public registration could grant the admin role when the email matched `INITIAL_ADMIN_EMAIL`, without a separately verified bootstrap flow.
- **Tasks:**
  - Remove privileged role assignment from ordinary public registration.
  - Implement a one-time, protected bootstrap procedure.
  - Require verified ownership of the configured identity and prevent repeated bootstrap.
  - Audit and log all admin role grants and changes.
- **Acceptance:** Public registration cannot create an administrator; bootstrap is one-time, authenticated, auditable, and tested.

### SEC-004 — Restrict privileged GitHub workflows to trusted refs and protected environments
- **Area:** CI/CD and production credentials
- **References:** Round 254
- **Previously reviewed paths:** `.github/workflows/publish-backend-image.yml`, `.github/workflows/production-db-backup.yml`, `.github/workflows/object-storage-smoke.yml`, `.github/workflows/backblaze-storage-smoke.yml`, `.github/workflows/stage-db-migrations.yml`
- **Observation:** Prior source review reported manual-dispatch paths that were not consistently constrained to trusted refs. Production backup preflight was also reported to receive secrets it did not need.
- **Tasks:**
  - Enforce trusted-ref conditions at the job level for image publishing and production-data workflows.
  - Put production credentials behind a dedicated GitHub Environment with required reviewers and deployment branch restrictions.
  - Remove database and object-storage secrets from preflight jobs; pass only non-secret presence/status signals where possible.
  - Scope storage credentials to dedicated test prefixes and minimum required operations.
  - Require explicit, auditable confirmation for destructive or production-adjacent operations.
- **Acceptance:** A workflow run from an untrusted branch cannot access production secrets or publish trusted release artifacts; preflight has no production credentials.

### SEC-005 — Add browser Content Security Policy
- **Area:** Frontend browser security
- **Reference:** Round 252
- **Previously reviewed paths:** `ai-backend/app/main.py`, Nginx configuration
- **Observation:** The prior review reported that CSP was absent from the examined response-header configuration.
- **Tasks:**
  - Inventory required script, style, image, connect, frame, and font origins.
  - Deploy a restrictive CSP in report-only mode first.
  - Resolve legitimate violations, including API streaming and project preview requirements.
  - Enforce the policy after monitoring; avoid broad unsafe directives unless justified and documented.
- **Acceptance:** Production responses carry an enforced CSP that supports required app functions and has no unexplained violations.

### SEC-006 — Make rate limiting resilient to Redis failure
- **Area:** API abuse protection
- **References:** Rounds 241, 255
- **Previously reviewed path:** `ai-backend/app/middleware.py`
- **Observation:** The review reported fail-open behavior for general rate limiting when Redis is unavailable, while authentication paths use stricter behavior.
- **Tasks:**
  - Define explicit per-route behavior for Redis outages.
  - Add bounded local fallback limits for expensive AI, upload, and other abuse-sensitive routes.
  - Preserve availability for low-risk routes where appropriate.
  - Add metrics and alerts for fallback activation and Redis failures.
- **Acceptance:** Redis outage does not silently remove all meaningful protection from expensive endpoints.

## P2 — Important hardening and integrity tasks

### SEC-007 — Enforce TOTP replay prevention
- **Area:** MFA
- **Reference:** Round 256
- **Previously reviewed path:** `ai-backend/app/auth/two_factor.py`
- **Observation:** The review reported TOTP verification with a time window but no persisted last-accepted counter.
- **Tasks:** Persist the last accepted counter per user; atomically reject equal or older counters; cover concurrent verification and clock-window behavior with tests.
- **Acceptance:** The same TOTP value cannot be accepted more than once.

### SEC-008 — Apply consistent lockout and throttling to MFA failures
- **Area:** MFA / brute-force protection
- **Reference:** Round 256
- **Previously reviewed path:** `ai-backend/app/auth/routes.py`
- **Observation:** The review reported that failed TOTP attempts were not reflected in the same account lockout counters as failed passwords.
- **Tasks:** Apply a documented combined or separate attempt budget for password and MFA; rate-limit by account and network context; avoid account-enumeration signals.
- **Acceptance:** Repeated MFA failures trigger bounded, tested protections without enabling trivial denial of service.

### SEC-009 — Revoke sessions after password changes
- **Area:** Credential lifecycle
- **Reference:** Round 256
- **Previously reviewed path:** `ai-backend/app/routers/users.py`
- **Observation:** The review reported inconsistent invalidation between ordinary password change and password reset.
- **Tasks:** Unify password-change and reset postconditions; increment token generation; revoke prior sessions; optionally preserve only the current session if explicitly designed and tested.
- **Acceptance:** All credentials covered by the documented policy are invalidated after password change/reset.

### SEC-010 — Revalidate and close authenticated WebSocket sessions
- **Area:** Realtime notifications
- **References:** Rounds 246, 252, 256
- **Previously reviewed path:** `ai-backend/app/routers/notifications.py`
- **Observation:** The review reported validation at connection time but no ongoing session/token-version revalidation.
- **Tasks:** Bind sockets to a session; close on revocation, account disable, password change, or token-generation change; add bounded periodic checks or event-driven revocation.
- **Acceptance:** A revoked or invalidated session cannot keep an authenticated WebSocket alive beyond the documented SLA.

### SEC-011 — Validate external source URLs before rendering
- **Area:** Frontend link safety
- **Reference:** Round 252
- **Previously reviewed path:** `ai-frontend/src/components/ChatMessage.jsx`
- **Observation:** Source URLs were reported to be assigned directly to anchor `href` values.
- **Tasks:** Parse and allow only explicitly supported schemes (normally HTTPS; HTTP only where deliberately required); reject script/data/file and other unsafe schemes; handle malformed URLs safely.
- **Acceptance:** Unsafe schemes never become clickable links; safe external links retain appropriate `rel` protections.

### SEC-012 — Prevent shared-conversation tokens from entering logs
- **Area:** Sensitive URL and observability data
- **References:** Rounds 252, 255
- **Previously reviewed paths:** `ai-backend/app/routers/shared_conversations.py`, `ai-backend/app/middleware.py`
- **Observation:** A share token in the request path may be captured by path-based metrics/logging.
- **Tasks:** Redact token-bearing path segments before logging/metrics; ensure reverse-proxy, hosting, tracing, and error logs also avoid raw tokens; consider moving bearer material out of paths in a versioned API design.
- **Acceptance:** Automated log tests confirm raw share tokens are not recorded.

### SEC-013 — Strengthen relational tenant/workspace integrity
- **Area:** Database integrity and tenant isolation
- **Reference:** Round 251
- **Previously reviewed models:** Workspace, Project, Conversation, FileAttachment
- **Observation:** Independent foreign keys were reported not to guarantee that related project/workspace identifiers belong to the same scope.
- **Tasks:** Evaluate composite foreign keys and unique constraints; design backward-compatible migrations; test cross-workspace mismatch attempts; confirm application authorization remains authoritative.
- **Acceptance:** The database rejects inconsistent cross-workspace relationships.

### SEC-014 — Standardize database TLS verification
- **Area:** Database transport security
- **Reference:** Round 251
- **Previously reviewed paths:** `ai-backend/app/config.py`, `ai-backend/app/database.py`
- **Observation:** TLS verification was reported to be enforced in selected staging/restore scripts but not explicitly guaranteed by the application connection configuration.
- **Tasks:** Document provider TLS guarantees; enforce certificate and hostname verification where supported; fail safely on invalid production TLS configuration.
- **Acceptance:** Production DB connections use verified TLS and invalid certificates are rejected.

### SEC-015 — Add RLS coverage guard for new tables
- **Area:** Database security governance
- **Reference:** Round 251
- **Previously reviewed migrations:** `0080`, `0081`, `0083`, `0084`
- **Observation:** RLS coverage was reported as migration-by-migration rather than automatically enforced for future tables.
- **Tasks:** Add CI/static checks that identify new public tables and require explicit RLS treatment; document privileged backend access and its authorization obligations.
- **Acceptance:** CI fails when a new applicable table lacks an explicit RLS decision.

### SEC-016 — Harden frontend dependency reproducibility and scanning
- **Area:** Software supply chain
- **Reference:** Round 253
- **Previously reviewed paths:** `ai-frontend/package.json`, `.github/workflows/ci.yml`
- **Observation:** The review reported no frontend lockfile and use of `npm install` rather than `npm ci`, with npm audit disabled in the install command.
- **Tasks:** Generate and commit a valid lockfile; use `npm ci`; add controlled npm audit/dependency scanning; define handling for advisories and exceptions.
- **Acceptance:** CI installs reproducibly from the committed lockfile and reports frontend dependency vulnerabilities.

### SEC-017 — Lock Python dependency sets and scan all shipped environments
- **Area:** Software supply chain
- **Reference:** Round 253
- **Previously reviewed paths:** backend, preview-builder, Python SDK dependency manifests
- **Observation:** Broad version ranges and partial pip-audit coverage were reported.
- **Tasks:** Introduce reproducible lockfiles and hashes where practical; scan backend, preview builder, and SDK independently; document update cadence and exceptions.
- **Acceptance:** Each shipped Python environment has a reproducible dependency set and vulnerability scan.

### SEC-018 — Pin container images and exclude sensitive build context
- **Area:** Container supply chain
- **Reference:** Round 253
- **Previously reviewed paths:** Dockerfiles and Compose files
- **Observation:** Some image tags were reported mutable and `.dockerignore` files absent from examined build contexts.
- **Tasks:** Pin production base/service images by digest; establish an update process; add appropriate `.dockerignore` files; verify no secrets or local artifacts enter build context.
- **Acceptance:** Production images are digest-pinned and build contexts exclude credentials and irrelevant files.

### SEC-019 — Produce SBOM and build provenance for published images
- **Area:** Artifact integrity
- **Reference:** Round 253
- **Previously reviewed path:** `.github/workflows/publish-backend-image.yml`
- **Observation:** Image digest output was reported, but SBOM, signed provenance/attestation, and verification gates were not found in the examined workflow.
- **Tasks:** Generate SBOM; attach provenance/attestation to the image; verify provenance and digest before release/deployment.
- **Acceptance:** Every released image has inspectable SBOM and verifiable build provenance.

### SEC-020 — Restrict proxy trust and normalize forwarded headers
- **Area:** Gateway / client IP integrity
- **Reference:** Round 255
- **Previously reviewed paths:** `ai-backend/app/config.py`, `ai-backend/app/middleware.py`, Nginx config
- **Observation:** Broad private network ranges were reported as trusted proxy networks.
- **Tasks:** Identify actual proxy hops and address ranges; trust only those; define a single canonical forwarded-header policy; test spoofed and malformed chains.
- **Acceptance:** Client IP and scheme cannot be controlled by untrusted forwarded headers.

### SEC-021 — Align SSE, WebSocket, proxy, and provider timeouts
- **Area:** Streaming reliability/security
- **Reference:** Round 255
- **Previously reviewed paths:** Nginx config and backend timeout settings
- **Observation:** A possible 60-second idle timeout alignment issue was reported; actual hosting edge behavior was not verified.
- **Tasks:** Document timeout budget end-to-end; configure explicit proxy read/send/body/header timeouts; test long idle streams, heartbeats, cancellation, and reconnect behavior in staging.
- **Acceptance:** Legitimate long-running streams are not cut off unexpectedly and resource consumption remains bounded.

### SEC-022 — Minimize CORS methods/headers and harden Nginx limits
- **Area:** HTTP gateway
- **Reference:** Round 255
- **Previously reviewed paths:** `ai-backend/app/main.py`, `ai-backend/nginx/nginx.conf`
- **Observation:** Broad CORS methods/headers and reliance on default client timeouts were reported.
- **Tasks:** Enumerate required methods/headers; restrict CORS; set explicit client header/body/send and keepalive limits appropriate to the app; test legitimate uploads and streaming.
- **Acceptance:** Only required cross-origin methods/headers are allowed and slow-client resource use is bounded.

### SEC-023 — Add explicit host and HTTP parser integration tests
- **Area:** Gateway protocol security
- **Reference:** Round 255
- **Observation:** Host allowlisting and proxy-chain behavior were not fully established; request-smuggling safety cannot be proven from static review alone.
- **Tasks:** Verify trusted Host configuration across hosting proxy, Nginx, and FastAPI; add safe staging integration tests for conflicting framing headers, malformed requests, and proxy normalization.
- **Acceptance:** Only expected hosts are accepted and proxy/backend parsing behavior is consistent. Do not run intrusive protocol tests against production.

### SEC-024 — Protect releases and deployment refs
- **Area:** Release governance
- **References:** Rounds 253, 254
- **Previously reviewed paths:** release/tag configuration and publish workflow
- **Observation:** A release was reported non-immutable and version-tag publication depended on tag patterns.
- **Tasks:** Protect release tags; enable immutable releases where available; bind releases to reviewed commit SHAs; require artifact provenance verification.
- **Acceptance:** A published release cannot silently move to different source/artifacts.

### SEC-025 — Require approval and least privilege for staging migrations/restores
- **Area:** Deployment governance
- **Reference:** Round 254
- **Previously reviewed paths:** `.github/workflows/stage-db-migrations.yml`, `.github/workflows/restore-to-supabase.yml`
- **Observation:** Source-level safeguards were reported, but GitHub Environment reviewer settings could not be confirmed from available read access.
- **Tasks:** Verify actual environment protection rules; require approval for sensitive staging operations; retain database identity and target guards; test only against isolated staging.
- **Acceptance:** Sensitive migration/restore jobs require protected refs, approved environments, and verified target identity.

### SEC-026 — Review TOTP setup/disable lifecycle and token claims
- **Area:** MFA / token validation
- **Reference:** Round 256
- **Previously reviewed paths:** `ai-backend/app/auth/two_factor.py`, `ai-backend/app/auth/security.py`
- **Observation:** The review noted potential gaps around session invalidation during MFA reconfiguration and optional JWT issuer/audience/required-claim validation.
- **Tasks:** Define reauthentication requirements for MFA changes; invalidate affected sessions/tokens; specify and validate issuer, audience, subject, expiry, issued-at, token type, and key identifier as appropriate.
- **Acceptance:** MFA changes require fresh proof of identity and invalidate credentials according to policy; tokens from unintended issuers/audiences are rejected.

## P3 — Operational follow-up / verification

### SEC-027 — Verify object URL cleanup and preview isolation
- **Area:** Frontend resource lifecycle
- **Reference:** Round 252
- **Previously reviewed paths:** `ai-frontend/src/components/FilesPanel.jsx`, `ProjectEditor.jsx`
- **Tasks:** Verify Blob URLs are revoked on close, replacement, and unmount; keep preview iframe sandbox minimal; test that preview content cannot access app origin or navigate the top-level page.
- **Acceptance:** No leaked object URLs after lifecycle tests; preview remains origin-isolated.

### SEC-028 — Add security headers and proxy configuration verification
- **Area:** Production configuration
- **References:** Rounds 252, 255
- **Tasks:** Verify the deployed Nginx/hosting configuration actually uses the production TLS template; confirm HSTS, frame protections, MIME sniffing protection, referrer policy, permissions policy, and CSP at the public edge.
- **Acceptance:** Automated staging checks validate the effective public response headers, not merely example config files.

### SEC-029 — Add security regression tests and coverage ledger
- **Area:** Security engineering process
- **References:** All reviewed rounds, especially 251–256
- **Tasks:**
  - Create one stable finding ID per unique issue; cross-link repeat observations instead of reopening duplicates.
  - Add tests for every accepted finding and record the exact file/function and test name.
  - Maintain a coverage matrix for reviewed, not reviewed, fixed, mitigated, accepted, and unverified areas.
  - Re-check current source before carrying forward old findings.
- **Acceptance:** Every open finding has an owner, priority, evidence, remediation, regression test, and current status; duplicate reports are linked to the same ID.

## Recommended execution order

1. **Immediate security boundaries:** SEC-004, SEC-003, SEC-001, SEC-002, SEC-005, SEC-006.
2. **Credential and session lifecycle:** SEC-009, SEC-010, SEC-007, SEC-008, SEC-026.
3. **Sensitive data and tenant integrity:** SEC-012, SEC-013, SEC-014, SEC-015.
4. **Supply chain and release integrity:** SEC-016 through SEC-019, SEC-024, SEC-025.
5. **Gateway and frontend hardening:** SEC-011, SEC-020 through SEC-023, SEC-027, SEC-028.
6. **Verification discipline:** SEC-029.

## Explicitly not done

- No code fixes or migrations were applied.
- No secrets, production settings, branch protections, or GitHub environments were changed.
- No workflows, deployments, backups, restores, or production tests were run.
- No claim is made that every finding is still present on the current default branch.
- This is a remediation backlog for AI Chat App only, not an implementation authorization or a security certification.
