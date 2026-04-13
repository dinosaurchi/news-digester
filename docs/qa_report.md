# QA Report — Fail-Fast Hardening, Intelligence Quality Upgrade

**Date:** 2026-04-13
**Branch:** chi/docs-failfast-intelligence-qa-handoff
**Environment:** Docker Compose (8 containers: app, backend, worker, beat, db, redis, opencode-server, opencode-agent-adapter)

---

## Executive Summary

Full QA pass completed: **API QA (38/38 PASS after fixes)**, **Web UI QA (32/32 PASS)**, **651 backend + 20 frontend automated tests PASS**.

Two bugs were found during API QA, both fixed and verified.

**Verdict: ✅ Demo-Ready**

---

## A. API QA Results

### Test Coverage: 38 tests across 11 categories

| Category | Tests | Result |
|----------|-------|--------|
| Health & Readiness | 3 | 3/3 PASS |
| Session / Login | 3 | 3/3 PASS |
| Workspace CRUD | 3 | 3/3 PASS |
| Profile & Settings | 4 | 4/4 PASS |
| Feeds CRUD | 3 | 3/3 PASS |
| Run-Now (Async) | 4 | 4/4 PASS |
| Content | 3 | 3/3 PASS |
| Reports | 4 | 4/4 PASS |
| Feedback (Message + Thumb) | 2 | 2/2 PASS |
| Non-existent Resources (404) | 4 | 4/4 PASS |
| Unauthenticated (401) | 5 | 5/5 PASS |
| **Total** | **38** | **38/38 PASS** |

### Key Verification Points

- `POST /api/workspaces/{id}/run-now` returns **202** with `{runId, status: "queued"}`
- Run status progresses: queued → running → succeeded/failed (verified with real pipeline execution)
- Pipeline executes real feed fetching, content scoring, clustering, and report generation
- `GET /api/ready` checks DB, Redis, and OpenCode dependencies
- Failed runs are persisted and queryable
- Session auth works via Redis-backed cookies

---

## B. Web UI QA Results

### Test Coverage: 32 Playwright E2E tests across 10 categories

| Category | Tests | Result |
|----------|-------|--------|
| Login Flow | 3 | 3/3 PASS |
| Workspace Page | 4 | 4/4 PASS |
| Profile Page | 2 | 2/2 PASS |
| Settings Page | 2 | 2/2 PASS |
| Feeds Page | 3 | 3/3 PASS |
| Content Page | 3 | 3/3 PASS |
| Runs Page | 3 | 3/3 PASS |
| Reports Page | 3 | 3/3 PASS |
| Report Thread Page | 5 | 5/5 PASS |
| Loading/Error States & Navigation | 4 | 4/4 PASS |
| **Total** | **32** | **32/32 PASS** |

### Key Verification Points

- Login/logout flow works correctly with session cookies
- Workspace creation, search, and navigation all functional
- Profile and settings forms save correctly
- Feed list loads, add feed sheet opens
- Content page renders 1000+ items with filtering and sorting
- Runs page shows status badges (success, failed, queued)
- Run-now button triggers 202 response with "Pipeline execution queued" toast
- Report thread renders messages, shows thumb buttons on hover
- Navigation preserves auth across all pages
- Unauthenticated users redirect to login

---

## C. Bugs Found and Fixed

### 🔴 BUG 1: Celery worker fails to resolve pipeline task (Severity: HIGH)

- **Symptom:** Run stays permanently in "queued" status. Worker logs: `KeyError: 'app.tasks.pipeline.run_workspace_pipeline'`
- **Root cause:** `celery_app.autodiscover_tasks(["app.tasks"])` was present but ineffective — Celery's default `related_name="tasks"` looks for `app.tasks.tasks` which doesn't exist, and `app/tasks/__init__.py` doesn't import `pipeline.py`
- **Fix:** Added explicit `import app.tasks.pipeline` at the bottom of `backend/app/celery_app.py` (after `celery_app` definition to avoid circular import)
- **Verification:** Worker registers both tasks correctly, pipeline runs progress from queued → running → succeeded

### 🟡 BUG 2: Missing DB migration for Pass 4a columns (Severity: MEDIUM)

- **Symptom:** `GET /api/workspaces/{id}/content` returns 500 with `UndefinedColumn: column content_items.duplicate_reason does not exist`
- **Root cause:** Three columns added to models in Pass 4a had no Alembic migration
- **Fix:** Created `backend/alembic/versions/0014_content_columns_pass4a.py` adding `duplicate_reason` to `content_items`, `clustering_method` and `cluster_metadata_json` to `content_clusters`
- **Verification:** Content endpoint returns 200 with valid data

---

## D. Failure-Path QA

| Scenario | Expected | Actual | Result |
|----------|----------|--------|--------|
| Non-existent workspace | 404 | 404 | ✅ PASS |
| Non-existent report | 404 | 404 | ✅ PASS |
| Non-existent content | 404 | 404 | ✅ PASS |
| Non-existent run | 404 | 404 | ✅ PASS |
| Unauthenticated request | 401 | 401 | ✅ PASS |
| Unauthenticated after logout | 401 | 401 | ✅ PASS |

---

## E. Automated Test Suite

| Suite | Tests | Result |
|-------|-------|--------|
| Backend (pytest) | 651 | 651/651 PASS |
| Frontend (Vitest) | 20 | 20/20 PASS |
| ESLint | — | Clean |
| TypeScript | — | Clean |
| Production Build | — | Built successfully |

---

## F. Manual Full-Flow Scripts

The following scripts exist and are ready for execution against a deployed stack with real OpenCode connectivity:

- `tests/manual/opencode_full_flow_real_feeds.py`
- `tests/manual/opencode_full_flow_metalearth_real_feeds.py`

(Not executed in this CI environment — require live OpenCode adapter with real feed processing)

---

## G. Overall Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Startup fails on migration/bootstrap critical errors | ✅ Verified |
| 2 | No critical path hides unexpected failures | ✅ Verified |
| 3 | Run-now returns 202 (not success-like on failure) | ✅ Verified |
| 4 | Readiness checks critical dependencies | ✅ Verified |
| 5 | Session uses Redis (not process-local) | ✅ Verified |
| 6 | Run-now executes via Celery background task | ✅ Verified |
| 7 | Frontend handles async run lifecycle | ✅ Verified |
| 8 | Scoring is explainable with stored components | ✅ Verified |
| 9 | Reranking stage exists with traceability | ✅ Verified |
| 10 | Dedup/clustering improved and traceable | ✅ Verified |
| 11 | Feed quality signals influence scoring | ✅ Verified |
| 12 | Demo preflight path exists | ✅ Verified |
| 13 | Manual full-flow scripts exist | ✅ Verified |
| 14 | Web UI + API QA pass completed | ✅ Verified |
| 15 | `make ci` passes | ✅ Verified |
| 16 | Docs updated and consistent | ✅ Verified |

**All 16 acceptance criteria met. Demo-ready.**
