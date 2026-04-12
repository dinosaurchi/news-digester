# Repair + Improvement Handoff — Fail-Fast Hardening, Intelligence Quality Upgrade, and QA

## Goal

Resolve the remaining correctness, fail-fast, readiness, and intelligence-quality issues in the current SME News Admin app.

This handoff is for a **focused repair-and-improve pass**, not a redesign.

The current app is already a real end-to-end MVP:
- real backend
- real feeds
- real report generation
- real report-thread chat
- real manual full-flow tests

However, it still has several problems:

1. it does **not fully obey fail-fast / no-hidden-errors**
2. readiness/health signaling is too weak
3. some critical operations are still too forgiving
4. `run-now` is still synchronous and hides failure semantics
5. intelligence quality can be improved with stronger retrieval/reranking, better feed-quality handling, and better dedup/clustering behavior
6. the app needs a dedicated **Web UI + API QA pass** after the changes

This handoff provides an explicit multi-pass plan with acceptance criteria per pass and overall.

---

## Current issues observed

### A. Startup is not fail-fast
In backend startup:
- migration failure is logged, but startup continues
- seed/bootstrap failure is logged, but startup continues

This must change.

### B. `run-now` still hides pipeline failure
The current `run-now` endpoint can return a failed run summary instead of surfacing the backend failure as an API error.

This violates fail-fast expectations.

### C. Broad catch-and-continue exists in core paths
There are still multiple broad `except Exception` patterns in:
- pipeline
- pipeline steps
- scoring
- report generation
- OpenCode interactions
- seed/bootstrap paths

Some of these may be acceptable only if the failure is truly optional.
Right now the codebase still mixes:
- optional degradation
- unexpected internal failure

Those need to be separated explicitly.

### D. Health/readiness is too shallow
The current health endpoint is effectively static.
It does not validate key dependencies such as:
- DB
- Redis
- OpenCode adapter

### E. `run-now` remains synchronous
This is acceptable for a tiny MVP, but it is now the next bottleneck for operational robustness and clean API behavior.

### F. Session handling is still process-local
This is okay for local demo use, but fragile for restart/multi-worker/containerized operation.

### G. Intelligence quality can be improved
The app has a real intelligence pipeline already, but the next quality step should improve:
- first-stage retrieval quality
- reranking precision
- dedup robustness
- cluster quality
- source/feed quality handling
- report relevance consistency for real client scenarios like Metal Earth

---

## Best-practice direction from current research

Use these best-practice directions as guidance for the implementation:

### 1. Health/readiness/startup should be separated
Use separate semantics for:
- startup checks
- readiness checks
- liveness checks

Readiness should verify critical dependencies used to serve traffic.
Startup should fail if critical initialization cannot complete.

### 2. Background task systems should track retries and started state explicitly
For long-running operations, task state and retry behavior should be explicit and observable.
Do not hide retryable errors inside request handlers.

### 3. Retrieval quality is typically improved with retrieve + rerank
A strong practical pattern is:
- fast first-stage retrieval
- slower higher-precision reranking on the shortlist

### 4. Use a hybrid first-stage retrieval/scoring approach
Do not rely only on one signal.
Use a combination of:
- lexical matching / BM25-like retrieval
- business-profile/topic/entity weighting
- source preferences and recency signals

> **Note:** The current codebase does not use pgvector or embedding-based retrieval.
> Introducing embeddings/vector search is a future option but out of scope for this repair pass.
> Hybrid scoring here means combining the existing text-based signals more effectively.

### 5. Intelligence quality should be measured, not just “felt”
Manual demo relevance is important, but you should also keep:
- deterministic score traces
- shortlist traces
- source-to-report traceability
- regression tests for scoring/dedup/report linkage

---

## Non-negotiable requirements

- obey fail-fast / no-hidden-errors
- no silent startup continuation on critical failure
- no success-looking API response when the underlying operation failed
- define optional vs fatal failures explicitly
- keep the current app architecture and improve it incrementally
- preserve real full-flow behavior
- add a dedicated QA pass for Web UI + API
- do not regress the existing manual full-flow tests
- keep the report thread experience intact
- `make ci` must pass after each pass is complete

---

## Scope boundaries

This handoff includes:
- backend fail-fast hardening
- readiness/health improvements
- pipeline failure semantics cleanup
- intelligence quality improvements
- background execution shape for run-now
- demo hardening
- Web UI + API QA

This handoff does **not** include:
- full product redesign
- customer-facing email delivery
- role/permission system overhaul
- production infra automation beyond reasonable readiness checks
- replacing OpenCode with a different agent framework

---

## Estimated effort per pass

| Pass | Scope | Relative Size |
|------|-------|---------------|
| 1 — Fail-fast startup & failure semantics | Focused fixes in startup + run-now | Small |
| 2 — Readiness, observability, session | Health endpoints + Redis sessions | Small–Medium |
| 3 — Async run-now | Wire existing Celery task + frontend polling | Small |
| 4a — Scoring, dedup, clustering improvements | Incremental improvements on existing code | Medium |
| 4b — Reranking stage | New capability, requires design decisions | Medium–Large |
| 4c — Feed quality handling | Independent concern | Small–Medium |
| 5 — Demo hardening | Scripts + fixtures + docs | Small |
| 6 — QA | Manual + automated validation | Medium (manual effort) |
| 7 — Cleanup & docs | Final polish | Small |

> **Note:** Pass 4 is significantly larger than Passes 1–3 combined. It is split into
> sub-passes (4a/4b/4c) so incremental quality gains can ship without blocking on the
> full reranking design.

---

## Implementation passes

Follow these passes in order.
Do not skip ahead if the earlier pass is unstable.
`make ci` must pass at the end of every pass before proceeding to the next.

# Pass 0 — Prerequisite: assess existing test infrastructure

## Goal
Understand what testing infrastructure exists so new tests build on it rather than creating a parallel structure.

## Tasks
- Identify test framework, runner, and configuration (pytest, conftest, fixtures)
- Identify existing test coverage and test directories
- Verify `make ci` runs and passes on the current codebase
- Document findings so subsequent passes can write tests consistently

## Acceptance criteria
- `make ci` passes on the current codebase before any changes begin
- Test infrastructure is understood — no guessing about where tests go or how to run them

---

# Pass 1 — Fail-fast startup and explicit failure semantics

## Goal
Make startup and critical runtime operations obey fail-fast / no-hidden-errors.

## Problems to fix
- startup continues after migration failure
- startup continues after critical bootstrap/seed failure
- `run-now` returns successful-looking output even when pipeline failed
- several critical code paths hide unexpected exceptions

## Implementation tasks

### 1. Backend startup must fail on critical initialization failure
In startup logic:
- if migrations fail → abort startup
- if critical bootstrap/setup fails → abort startup
- only allow non-fatal optional steps to continue when explicitly marked optional

Do not log-and-continue for critical initialization.

### 2. Define fatal vs optional initialization explicitly
Refactor startup into clearly separated steps:
- critical: DB connection sanity, migrations, admin bootstrap if required
- optional: only things explicitly safe to skip

Document this distinction in code comments and README.

### 3. Fix `run-now` failure semantics
Change `POST /api/workspaces/{id}/run-now` so that:
- if pipeline fails, the endpoint returns an explicit error response
- the failed run is still persisted for inspection
- the API response must not look like a success result

Recommended:
- persist failed run + events
- return structured 5xx or appropriate failure response containing:
  - runId
  - error summary
  - failure stage if known

### 4. Remove broad catch-and-continue in critical code paths
Audit and fix broad exception handling in:
- startup
- run-now
- pipeline orchestration
- report generation
- scoring
- OpenCode invocation
- seed/bootstrap

Use this rule:
- if the failure means the requested operation cannot be trusted → re-raise / fail
- only degrade gracefully when the degraded behavior is explicitly intended and visible

### 5. Standardize error shape
Introduce a consistent error response shape where appropriate, for example:
- error code
- message
- details
- runId if relevant
- stage if relevant

## Tests

### Automated
- startup migration failure test
- startup bootstrap failure test
- run-now pipeline failure test
- error response schema tests
- unexpected exception propagation tests for critical pipeline paths

### Manual
- intentionally break migration setup and verify startup fails
- intentionally break bootstrap/admin init and verify startup fails
- force pipeline failure and verify run-now returns an error response
- verify failed run is still visible in Runs UI/API

## Acceptance criteria
- app does not start if migrations fail
- app does not start if critical bootstrap fails
- run-now no longer returns success-like output on pipeline failure
- critical unexpected failures surface clearly
- no critical path still silently hides errors
- `make ci` passes

---

# Pass 2 — Readiness, liveness, observability, and session hardening

## Goal
Make the system operationally inspectable and safer for demos/runs.

## Problems to fix
- `/api/health` is too shallow
- dependency readiness is not checked
- session handling is still too fragile for demo environments
- request/task observability can be improved

## Implementation tasks

### 1. Split health endpoints
Implement separate endpoints or clearly separate semantics for:
- liveness
- readiness
- startup/boot diagnostics if useful

Recommended behavior:
- liveness: app process is alive
- readiness: app can serve real requests safely
- readiness should validate at least:
  - DB connectivity
  - Redis connectivity if required for current mode
  - OpenCode adapter reachability/config sanity if required for report/chat flows

### 2. Improve request and run observability
Add or strengthen:
- structured logs
- request correlation / request IDs if practical
- run event clarity
- failure stage tagging
- explicit logging around OpenCode request/response boundaries (without leaking sensitive data)

### 3. Harden session handling
Replace the process-local in-memory session dict (`services/session.py`) with Redis-backed session storage.

Redis is already in the stack as the Celery broker — this is the minimal-effort path that solves process-local fragility without a full auth overhaul.

Minimum requirement:
- session survives app restart
- multiple app processes share session state via Redis
- session TTL is explicit and configurable

### 4. Improve readiness reporting for demo use
Add a small preflight/readiness summary that makes it easy to tell whether a demo environment is ready:
- DB ready
- Redis ready
- OpenCode ready
- migrations up to date

## Tests

### Automated
- liveness endpoint test
- readiness success/failure tests for DB
- readiness success/failure tests for Redis if applicable
- readiness success/failure tests for OpenCode adapter/config
- session persistence tests

### Manual
- bring DB down and verify readiness fails
- bring Redis down and verify readiness behavior is correct
- misconfigure OpenCode and verify readiness reports it
- restart app and verify session behavior does not break unexpectedly

## Acceptance criteria
- health semantics are separated and meaningful
- readiness checks critical dependencies
- operators can tell if the app is demo-ready
- session uses Redis, no longer process-local fragile
- observability is improved enough for debugging real runs
- `make ci` passes

---

# Pass 3 — Move `run-now` to background execution with explicit task state

## Goal
Make `run-now` operationally correct and more robust by moving execution out of the request path.

## Problems to fix
- `run-now` is synchronous
- long requests are harder to manage
- failures and retries are harder to reason about
- API semantics are not ideal for long-running operations

> **Existing infrastructure:** `tasks/pipeline.py` already defines `run_workspace_pipeline`
> as a Celery task. The primary work is wiring the endpoint to dispatch this existing task
> and updating the API contract — not building a task system from scratch.

## Implementation tasks

### 1. Change run-now API contract
Recommended behavior:
- `POST /api/workspaces/{id}/run-now` creates a run record and dispatches a task
- return immediately with:
  - runId
  - queued/running status
  - task metadata if useful

### 2. Execute pipeline in worker/task context
Move pipeline execution into Celery task flow or equivalent background execution path.

### 3. Make task lifecycle explicit
Ensure run/task state is visible in:
- ProcessingRun
- ProcessingRunEvent timeline

Recommended states:
- queued
- running
- succeeded
- failed
- retrying if you choose to expose it

### 4. Define retry policy explicitly
Apply retry behavior only to recoverable failures.
Do not retry programmer errors or invalid config errors.

### 5. Preserve fail-fast semantics
Background execution must still be fail-fast in the correct way:
- unexpected failure marks run failed
- no hidden success
- no swallow-and-continue in the core pipeline

### 6. Update frontend for async run lifecycle
The frontend must handle the new async contract:
- **RunsPage / WorkspaceOverviewPage:** poll or use SSE for run status updates (queued → running → succeeded/failed)
- **Run-now button:** show "queued" / "running" intermediate states instead of blocking until completion
- **API hooks/adapters:** update to handle 202 Accepted instead of 201 with final result
- **Error display:** surface failed-run errors from the polling response, not the dispatch response

## Tests

### Automated
- run-now returns queued/running response
- worker executes run and updates status
- failed worker execution marks run failed
- retryable error behavior test if retries are added
- non-retryable error behavior test

### Manual
- trigger run-now from UI/API
- verify run status progresses correctly
- verify report appears after completion
- verify failed run appears correctly with errors
- verify UI does not misrepresent queued vs completed state

## Acceptance criteria
- run-now no longer blocks on the full pipeline
- run status lifecycle is explicit and inspectable
- failed runs remain visible and truthful
- task execution is compatible with fail-fast policy
- frontend handles async run lifecycle correctly
- `make ci` passes

---

# Pass 4a — Scoring, dedup, and clustering improvements

## Goal
Improve relevance consistency and demo quality by strengthening existing scoring, dedup, and clustering — building on what already exists.

> **Current state:** Scoring uses keyword matching (BM25-style), competitor detection,
> freshness decay, source authority, and feedback adjustment. Clustering is text-based
> (URL normalization, title fingerprint, token overlap). There are no embeddings or
> pgvector. The existing shortlist step already calls OpenCode for LLM-based refinement.

## Implementation tasks

### 1. Make scoring pipeline explicitly hybrid
Strengthen first-stage scoring with a weighted combination of the existing signals:
- lexical relevance (BM25 or equivalent) — already exists
- source preferences — already exists
- topic/entity preference weights — already exists
- recency signal — already exists (freshness decay)
- content-type/source-type priors — new

Store score components separately so debugging is possible.
Make weights configurable per workspace or globally.

### 2. Improve dedup behavior
Audit and tune dedup so near-duplicate content is handled consistently.

Requirements:
- deterministic duplicate key strategy where possible
- improve token-overlap thresholds for near-duplicate detection
- duplicate reasons visible for debugging
- avoid report pollution from repeated syndicated stories

### 3. Improve clustering behavior
Audit cluster creation and cluster assignment.
Improve:
- thresholding
- singleton handling
- cluster metadata
- explainability in Content detail

### 4. Strengthen report relevance for client-specific workspaces
Add targeted regression checks for scenarios like Metal Earth:
- licensed/franchise signals
- collectibles/hobby relevance
- themed category relevance (aviation, architecture, etc.)
- avoid obvious irrelevant topic drift

## Tests

### Automated
- scoring component tests
- hybrid score composition tests
- dedup regression tests
- clustering regression tests
- content-to-report traceability tests
- Metal Earth scenario regression tests if feasible with fixtures

### Manual
- run the generic real-feeds full-flow test
- run the Metal Earth full-flow test
- inspect report relevance manually
- verify clustered/deduped content in Content UI

## Acceptance criteria
- scoring is more explainable and traceable
- score components are stored separately for debugging
- dedup and clustering are less noisy
- reports are more consistently relevant for client-themed workspaces
- source-to-report traceability remains intact
- `make ci` passes

---

# Pass 4b — Reranking stage

## Goal
Add a second-stage reranking step to improve shortlist precision beyond what single-pass scoring provides.

> **Current state:** `services/shortlist.py` already calls OpenCode for LLM-based
> shortlist refinement. This pass formalizes and strengthens that into an explicit
> rerank stage with traceability.

## Implementation tasks

### 1. Add explicit reranking stage
Before report generation:
- retrieve a wider candidate pool from first-stage scoring
- rerank the candidate pool with a higher-precision stage

Recommended approach (in order of pragmatism):
1. Strengthen the existing OpenCode/LLM shortlist refinement with explicit prompt engineering and traceability
2. If higher precision is needed later, evaluate a cross-encoder reranker (this requires new ML dependencies — treat as a future option, not a requirement)

### 2. Persist reranking artifacts
Persist:
- candidate set (pre-rerank)
- reranked shortlist (post-rerank)
- reasons/scores if practical

### 3. Shortlist/rerank tests
- shortlist/rerank regression tests
- verify candidate set vs reranked shortlist is traceable

## Tests

### Automated
- shortlist/rerank tests
- candidate-to-report traceability tests

### Manual
- inspect shortlist and source traceability
- compare pre-rerank vs post-rerank shortlists for quality

## Acceptance criteria
- reranking stage exists and improves shortlist precision
- pre-rerank and post-rerank artifacts are persisted
- `make ci` passes

---

# Pass 4c — Feed/source quality handling

## Goal
Improve handling of low-quality, stale, or noisy feed sources.

## Implementation tasks

### 1. Improve feed/source quality handling
Add stronger heuristics/controls for source quality:
- stale feed handling (detect feeds that haven't returned new content)
- feed reliability history (track fetch success/failure rates)
- feed health weighting in scoring if useful
- low-signal or noisy-source suppression where justified

## Tests

### Automated
- feed quality/staleness detection tests
- source weighting tests

### Manual
- verify stale feeds are flagged/downweighted
- verify noisy sources don't dominate reports

## Acceptance criteria
- feed quality signals exist and influence scoring
- operators can identify problematic feeds
- `make ci` passes

---

# Pass 5 — Demo hardening and deterministic preflight tooling

## Goal
Reduce demo-day surprises and make the environment easier to validate quickly.

## Problems to fix
- real demo still depends on external systems/feeds/models
- no clean preflight readiness gate
- no explicit demo preparation flow

## Implementation tasks

### 1. Add demo preflight command/script
Create a script or command that verifies:
- backend readiness
- DB ready
- Redis ready
- OpenCode ready
- at least one known-good feed validates
- critical routes/pages load
- maybe a quick report-thread smoke path if affordable

### 2. Add known-good demo fixtures / seed path
Support a safe path for demo preparation:
- create or seed a known-good workspace
- configure known-good feeds
- optionally pre-warm one report/thread

### 3. Add feed fallback guidance
Document and optionally encode fallback feed choices for demos if a public source is flaky.

### 4. Improve demo documentation
Add a short demo README/checklist covering:
- env vars
- startup
- preflight
- known-good workspace
- what to do if one feed fails
- what to do if OpenCode adapter is unavailable

## Tests

### Automated
- preflight script smoke test if practical
- readiness command test if practical

### Manual
- run preflight on the deployed stack
- validate known-good workspace flow
- validate backup feed flow
- validate Metal Earth full-flow script on the target environment

## Acceptance criteria
- demo operator can determine readiness quickly
- demo environment can be pre-warmed predictably
- known-good recovery path exists for flaky feeds
- `make ci` passes

---

# Pass 6 — Full QA pass: Web UI + API + manual full-flow validation

## Goal
Verify the changes work properly across the real app, not just in isolated tests.

## Scope
This pass is mandatory.
It must validate:
- backend API correctness
- frontend integration correctness
- UI states
- report-thread behavior
- manual real-feed flows
- failure-path behavior

## QA plan

### A. API QA
Verify with real API calls:
- startup/readiness endpoints
- workspace CRUD
- profile/settings CRUD
- feeds CRUD + feed test
- run-now dispatch + run detail
- reports list/detail
- report regenerate
- report thread message send
- thumb up/down feedback
- content list/detail
- runs list/detail
- preferences/feedback endpoints

### B. Web UI QA
Verify in the browser:
- login/session flow if still present
- workspace creation/edit flow
- Profile page save behavior
- Settings page save behavior
- Feeds page add/edit/test/delete behavior
- Content page filtering and detail view
- Runs page status/detail visibility
- Reports page list behavior
- Report Thread page:
  - report rendering
  - source viewing
  - regenerate
  - user feedback send
  - agent response display
  - thumb up/down
- loading states
- error states
- retry states
- failed-run visibility

### C. Manual full-flow QA
Run both:
- `tests/manual/opencode_full_flow_real_feeds.py`
- `tests/manual/opencode_full_flow_metalearth_real_feeds.py`

Run them against the target deployed/demo stack.

### D. Failure-path QA
Explicitly verify:
- readiness failure when dependency is broken
- pipeline failure surfaces correctly
- failed run is visible in UI/API
- no success-looking response is returned on true failure

## Deliverables for this pass
Produce:
- QA report
- list of issues found
- fixes applied
- screenshots or logs where useful
- final “demo-ready / not demo-ready” verdict

## Acceptance criteria
- Web UI works correctly with the updated backend
- API behavior matches UI expectations
- both manual full-flow scripts pass
- failure-path behavior is truthful and visible
- no major regression remains
- `make ci` passes

---

# Pass 7 — Final cleanup, docs, and acceptance signoff

## Goal
Leave the repo in a clean state with explicit operational guidance.

## Implementation tasks
- update README/backend docs for:
  - fail-fast behavior
  - readiness endpoints
  - background run-now behavior
  - demo preflight
  - manual full-flow tests
- add comments where behavior might otherwise be misunderstood
- remove stale code paths made obsolete by the repair passes
- ensure test commands are documented clearly

## Acceptance criteria
- docs match actual behavior
- no obsolete workaround logic remains
- repo is understandable for the next implementer/operator
- `make ci` passes

---

## Overall acceptance criteria

All of the following must be true before the work is considered complete:

1. startup fails on migration/bootstrap critical errors
2. no critical path still hides unexpected failures
3. run-now no longer returns success-like output when the pipeline failed
4. readiness checks critical dependencies meaningfully
5. session handling uses Redis, no longer fragile process-local-only state
6. run-now executes via the existing Celery background task flow
7. frontend handles async run lifecycle (polling, intermediate states)
8. scoring is more explainable with separately stored score components
9. reranking stage exists and improves shortlist precision
10. dedup/clustering quality is improved and traceable
11. feed quality signals exist and influence scoring
12. demo preflight path exists
13. both manual full-flow scripts pass on the target stack
14. Web UI + API QA pass is completed successfully
15. `make ci` passes after every pass
16. docs are updated and consistent

---

## Suggested files likely to change

Backend:
- `backend/app/main.py`
- `backend/app/api/runs.py`
- `backend/app/api/session.py`
- `backend/app/services/pipeline.py`
- `backend/app/services/pipeline_steps.py`
- `backend/app/services/scoring.py`
- `backend/app/services/report_generator.py`
- `backend/app/services/shortlist.py`
- `backend/app/services/session.py`
- `backend/app/celery_app.py`
- `backend/app/tasks/pipeline.py`
- `backend/app/tests/...`

Potential data/migration files:
- migrations / alembic revisions

Frontend (React/Vite TypeScript at `src/`):
- `src/pages/RunsPage.tsx` — run status polling for async run-now
- `src/pages/ReportsPage.tsx` — report availability after async completion
- `src/pages/ReportThreadPage.tsx` — report thread behavior
- `src/pages/WorkspaceOverviewPage.tsx` — run-now button + status display
- API hooks/adapters — update for async run-now contract (202 + polling)
- Session-related code if auth/session storage changes

QA / scripts:
- manual test scripts
- preflight script
- docs / README

---

## Final instruction

Do not treat this as cosmetic cleanup.

This pass should:
- enforce fail-fast behavior
- remove hidden-error behavior
- improve operational truthfulness
- improve intelligence quality in a measurable/debuggable way
- verify the result through real Web UI + API QA and full-flow manual tests
