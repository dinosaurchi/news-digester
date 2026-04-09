# Pass 7 Current State Handoff

**Date:** 2026-04-09
**Branch:** `chi/implement-real-ai-backend`
**Status:** Stabilized in the follow-up fix. Keep this note for historical context; do not follow the obsolete “critical issue” instructions below without first checking current branch HEAD.

## Stabilization Update — 2026-04-09

The default deployment contract was changed:

- `make up` starts only the core app/backend/worker/beat/db/redis stack.
- `OPENCODE_ENABLED` defaults to `false` in Compose and backend settings.
- OpenCode is opt-in: `OPENCODE_ENABLED=true docker compose --profile opencode up --build -d`.
- The backend OpenCode client targets the adapter `/v1/runs` + `/v1/sessions/{id}/result` contract; `/v1/chat` is not used.
- The optional adapter is built from `services/opencode-agent-adapter`.
- Report regeneration appends a regenerated `system` message to the same report thread.
- If `OPENCODE_ENABLED=true` and the adapter/provider fails, the backend raises the OpenCode error and the processing run is marked failed. There is no silent fallback in the enabled path.

---

## What Was Implemented

Pass 7 (Relevance Pipeline and Report Quality) was implemented across 40 TODO items in seven sub-passes:

| Sub-pass | Description |
|----------|-------------|
| **7.0** | LLM Infrastructure — opencode-server/adapter Compose services, OpenCode client layer |
| **7.1** | Content Dedup & Clustering — 4-phase: URL match, title fingerprint, similarity, singletons |
| **7.2** | Cheap Relevance Filtering & Scoring — keyword, competitor, freshness, source authority, BM25 |
| **7.3** | Shortlist Generation — cluster dedup, score sorting, size cap, optional LLM refinement |
| **7.4** | Report Generation — deterministic template + LLM path, source-backed markdown |
| **7.5** | Feedback-Aware Quality Hooks — topic/source preference adjustments |
| **7.6** | QA, hardening, documentation |

---

## Test Status

| Suite | Count | Status |
|-------|-------|--------|
| Backend tests | **407 passing** | All green |
| Frontend tests | **20 passing** | All green |
| Production build | **Passes** | `npm run build` succeeds |

Tests work because `conftest.py` forces `OPENCODE_ENABLED=false`, so no LLM calls are attempted.

---

## Deployment Status

- Core 6 services (`app`, `backend`, `worker`, `db`, `redis`, `celery-beat`) deploy and run healthy via `make up`
- `opencode-server` and `opencode-agent-adapter` are behind `profiles: ["opencode"]` so they do **not** block `make up`
- Images for opencode services are not publicly available — they require custom builds
- All database migrations apply cleanly

---

## Historical Critical Issue — Fixed In Follow-Up

Previously, `OPENCODE_ENABLED` was set to `"true"` in `docker-compose.yml` while the opencode-agent-adapter was not running. That made every `run-now` call fail. The follow-up fix changed the default to explicit deterministic/local mode: `OPENCODE_ENABLED=false`.

### What happens

Pipeline steps 1–4 work fine:

1. `fetch_feeds` — completed
2. `normalize_content` — completed
3. `cluster_content` — completed
4. `score_content` — completed

Step 5 fails:

5. `select_shortlist` — **error**: the pipeline creates an `OpenCodeClient` (because `OPENCODE_ENABLED=true`) and passes it to `select_shortlist()`, which calls `_refine_via_llm()`, which calls `client.refine_shortlist()`, which tries to reach `http://opencode-agent-adapter:8080` and gets connection refused.

Step 6 never runs:

6. `generate_report` — never reached

### Actual error from live verification

```
"error": "OpenCode adapter is unreachable at http://opencode-agent-adapter:8080"
```

This error surfaces in the run detail response (`GET /api/runs/{id}`) as the `message` field on the `select_shortlist` pipeline step event.

---

## Historical Fix Options

There are three options:

### Option A: Set `OPENCODE_ENABLED=false` in docker-compose.yml (Recommended)

Change line 40 of `docker-compose.yml` from:
```yaml
OPENCODE_ENABLED: "true"
```
to:
```yaml
OPENCODE_ENABLED: "false"
```

This makes the pipeline use deterministic scoring and template-based report generation. No LLM calls are attempted. All 6 pipeline steps complete successfully. This is what tests already do (via `conftest.py`).

### Option B: Deploy actual opencode services

Build or obtain real images for `opencode-server` and `opencode-agent-adapter`, then start them with:
```bash
docker compose --profile opencode up -d
```

### Option C: Silent fallback (FORBIDDEN)

Make the pipeline gracefully skip LLM steps when the adapter is unreachable. **Do not do this.** The earlier handoff document explicitly states: "fail fast and explicitly when a required Pass 7 stage fails; do not hide failures behind silent fallback output."

---

## Historical Verification Before Stabilization

| Endpoint/Feature | Status |
|------------------|--------|
| `GET /api/health` | 200 OK |
| `GET /api/workspaces` | Returns workspaces |
| `POST /api/workspaces/{id}/run-now` | Previously failed at step 5 when OpenCode was enabled without adapter |
| `GET /api/runs/{id}` | Returns full run with step details and error info |
| `GET /api/workspaces/{id}/reports` | Previously empty after failed runs |
| `GET /api/workspaces/{id}/content` | Returns content items (with scores from step 4) |
| Feedback endpoints | Working |
| All CRUD endpoints | Working |

## Historical Broken State Before Stabilization

| Feature | Reason |
|---------|--------|
| Full pipeline execution | Fails at `select_shortlist` (step 5) |
| Report generation | Never reached (step 6) |
| Scheduled daily report generation | Would also fail at `select_shortlist` |

---

## Recommended Follow-Up (Current)

1. **Default-path QA** — run `make up`, trigger `run-now`, and confirm all 6 steps complete with a report.
2. **OpenCode-path QA when credentials are available** — run `OPENCODE_ENABLED=true docker compose --profile opencode up --build -d`, trigger `run-now`, and confirm `/v1/runs` creates completed adapter sessions.
3. **Do not reintroduce `/v1/chat`** — the supported adapter contract is `/v1/runs` plus `/v1/sessions/{id}/result`.

---

## Files of Note

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Service definitions, `OPENCODE_ENABLED` env var (line 40) |
| `backend/app/config.py` | `Settings` class with `OPENCODE_ENABLED`, `OPENCODE_BASE_URL`, etc. |
| `backend/app/services/pipeline.py` | 6-step pipeline; creates `OpenCodeClient` when enabled (line 205) |
| `backend/app/services/opencode_client.py` | LLM client layer; raises on unreachable adapter (line 226) |
| `backend/app/services/dedup.py` | URL canonicalization, title fingerprinting, near-duplicate detection |
| `backend/app/services/clustering.py` | Cluster assignment, representative selection |
| `backend/app/services/scoring.py` | Keyword/theme/BM25/competitor/freshness scoring |
| `backend/app/services/shortlist.py` | Ranked selection with cluster dedup, size cap, LLM refinement |
| `backend/app/services/report_generator.py` | Structured markdown report generation |
| `backend/app/tests/conftest.py` | Sets `OPENCODE_ENABLED=false` for all tests |
| `docs/2026-04-09_pass7_completion_note.md` | Earlier completion note (written before the live issue was found) |

---

## Branch Info

- **Branch:** `chi/implement-real-ai-backend`
- **Total commits for Pass 7:** 24
- **Working tree:** clean
- **Latest commit:** `aa969a1` — `[AI] fix: gate opencode services behind docker compose profile (Pass 7.6)`
