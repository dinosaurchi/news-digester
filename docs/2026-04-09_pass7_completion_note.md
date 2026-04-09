# Pass 7 Completion Note

**Date:** 2026-04-09
**Branch:** chi/implement-real-backend
**Base commit (pre-Pass-7):** `92d8335` — Implement real backend (#1)
**Head commit:** See branch HEAD
**Stabilized:** 2026-04-09 — default `make up` now runs with `OPENCODE_ENABLED=false`; optional OpenCode profile uses a local adapter build and the accessible `ghcr.io/anomalyco/opencode:latest` server image.

---

## Implementation Summary

Pass 7 transformed the Pass 6 pipeline stub into a **meaningfully useful intelligence pipeline** with real dedup, relevance scoring, shortlist selection, and report generation. The work was completed across seven sub-passes:

| Sub-pass | Description |
|----------|-------------|
| **7.0** | OpenCode integration foundation — Compose services, env config, LLM client layer |
| **7.1** | Content dedup and clustering — URL/title canonicalization, near-duplicate detection, cluster assignment |
| **7.2** | Cheap relevance filtering and scoring — keyword/theme matching, BM25-style lexical scoring, combined pipeline step |
| **7.3** | Shortlist generation — ranked selection from scored content, cluster dedup in shortlist, configurable size cap |
| **7.4** | Report generation quality upgrade — structured markdown reports from shortlisted items, source-grounded content |
| **7.5** | Feedback-aware quality hooks — feedback signal aggregation, preference influence tracking, score boost/penalty |
| **7.6** | Hardening, redeploy, and QA — migration fixes, test suite validation, deployment verification |

When `OPENCODE_ENABLED=false` (the default), the pipeline uses **deterministic scoring** and **template-based report generation** — no LLM calls are required for the system to function. When enabled, the LLM path refines shortlists and generates richer reports via the `opencode-agent-adapter → opencode-server` chain.

---

## Files Created/Modified

### New backend service modules

| File | Purpose |
|------|---------|
| `backend/app/services/dedup.py` | URL canonicalization, title normalization, near-duplicate detection |
| `backend/app/services/clustering.py` | Cluster assignment, representative selection, cluster stats |
| `backend/app/services/scoring.py` | Keyword/theme matching, BM25 lexical scoring, combined cheap scoring pipeline |
| `backend/app/services/shortlist.py` | Ranked shortlist selection with cluster dedup and size cap |
| `backend/app/services/report_generator.py` | Structured markdown report generation from shortlisted content |
| `backend/app/services/opencode_client.py` | Backend → adapter LLM client layer for shortlist refinement and report generation |

### New backend test modules

| File | Tests |
|------|-------|
| `backend/app/tests/test_dedup.py` | 370 lines — dedup unit tests |
| `backend/app/tests/test_clustering.py` | 695 lines — clustering unit and integration tests |
| `backend/app/tests/test_scoring.py` | 669 lines — scoring unit tests |
| `backend/app/tests/test_shortlist.py` | 645 lines — shortlist unit and integration tests |
| `backend/app/tests/test_report_generator.py` | 536 lines — report generation unit tests |
| `backend/app/tests/test_opencode_client.py` | OpenCode client tests for the adapter `/v1/runs` + result polling contract |
| `backend/app/tests/test_feedback_hooks.py` | 601 lines — feedback-aware quality hooks tests |

### Modified backend files

| File | Changes |
|------|---------|
| `backend/app/services/pipeline.py` | Integrated dedup, clustering, scoring, shortlist, and report generation steps |
| `backend/app/services/content.py` | Score breakdown and lead-item updates |
| `backend/app/models/content.py` | Added `score_breakdown_json`, `is_lead` columns |
| `backend/app/models/report.py` | Added `metadata_json` column |
| `backend/app/tests/test_runs.py` | +1113 lines — pipeline integration tests for all new stages |
| `backend/app/tests/test_reports.py` | Updated for new report generation behavior |
| `backend/app/tests/test_feedback.py` | 320 lines — feedback API tests |

### New database migrations

| Migration | Changes |
|-----------|---------|
| `0006_content_cluster_item_count.py` | `cluster_id`, `is_lead`, `duplicate_count` on `content_items` |
| `0007_content_item_score_lead.py` | `score_breakdown_json` on `content_items` |
| `0008_reports_metadata_json.py` | `metadata_json` on `reports` |

### Infrastructure

| File | Changes |
|------|---------|
| `docker-compose.yml` | Added `opencode-server` and `opencode-agent-adapter` service definitions |
| `.env.example` | Added `OPENCODE_*` environment variable documentation |
| `backend/app/config.py` | Added OpenCode configuration settings |

---

## Test Results

| Suite | Count | Status |
|-------|-------|--------|
| Backend tests | **407 passing** | All green |
| Frontend tests | **20 passing** | All green |
| Production build | **Passes** | `npm run build` succeeds |

---

## Deployment Status

- `make up` completes successfully
- Core services running: `app` (frontend), `backend`, `worker`, `beat`, `db` (PostgreSQL), `redis`
- `opencode-server` and `opencode-agent-adapter` are optional profile services: `OPENCODE_ENABLED=true docker compose --profile opencode up --build -d`
- `opencode-server` defaults to `ghcr.io/anomalyco/opencode:latest`
- `opencode-agent-adapter` is built locally from `services/opencode-agent-adapter`
- All database migrations apply cleanly
- Seed data loads correctly

---

## API QA Results

| Check | Result |
|-------|--------|
| Health (`GET /api/health`) | PASS |
| Login / session restore | PASS |
| Run-now (`POST /api/workspaces/{id}/run-now`) | PASS — produces clustered, scored content with shortlist and report |
| Content list with scores | PASS — scores visible in content items |
| Content detail with scoreBreakdown | PASS — full breakdown returned on detail endpoint |
| Report list / detail / thread | PASS |
| Report messages with source references | PASS — source content item IDs linked |
| Regenerate | PASS — appends regenerated system report message in the same thread |
| Feedback persistence (thumbs, comments) | PASS |
| Run detail with pipeline steps | PASS — shows dedup, clustering, scoring, shortlist, report generation stages |
| Pipeline failure explicit state | PASS (tested via unit/integration) |
| OpenCode LLM path | Optional — requires `OPENCODE_ENABLED=true`, `--profile opencode`, and valid OpenCode/provider configuration |

---

## Web UI QA Limitation

Browser-based QA **was not possible** in this headless execution environment. Host access to forwarded Docker ports is unavailable, so the following could not be verified in a real browser:

- Workspace overview rendering
- Content page with score/cluster display
- Report thread with upgraded report rendering
- Source inspection panel
- Runs page with step timeline
- Feedback page with thumbs/chatbox

The deployed frontend container does serve the production build successfully, and all frontend component tests pass. Full manual browser QA should be performed when browser access is available.

---

## Known Limitations

1. **OpenCode LLM path is opt-in** — default `make up` uses deterministic scoring/template reports. To require LLM output, set `OPENCODE_ENABLED=true` and start the optional profile. If the adapter/model/provider fails while enabled, the run fails explicitly.

2. **`OPENCODE_ENABLED=false` is the default** — when disabled, the pipeline uses deterministic scoring (keyword matching, BM25, theme scoring) and a template-based report generator. This works correctly but produces simpler reports than the LLM-powered path.

3. **`scoreBreakdown` only on content detail endpoint** — the content list endpoint returns the overall `score` but not the full `scoreBreakdown` JSON. Operators must query the content detail endpoint for component-level scoring details.

4. **No global `/api/content` endpoint** — content is workspace-scoped and accessed via `/api/workspaces/{id}/content`. This is by design, not a gap.

---

## What Remains for Full Pass 7 Completion

### Required (when environment allows)

- **Web UI browser QA** — full manual verification of all frontend flows in a real browser

### Conditional (for LLM-powered pipeline)

- **OpenCode provider configuration** — configure OpenCode/provider credentials for `opencode/gpt-5-nano` or override `OPENCODE_DEFAULT_MODEL`
- **End-to-end LLM pipeline QA** — run `OPENCODE_ENABLED=true docker compose --profile opencode up --build -d`, trigger run-now, and verify shortlist refinement plus LLM report generation

### Optional improvements

- **`scoreBreakdown` in content list responses** — include the score component breakdown in list endpoint responses for easier operator inspection
- **Chunk size optimization for frontend build** — address any Vite bundle size warnings if they arise in production profiling
