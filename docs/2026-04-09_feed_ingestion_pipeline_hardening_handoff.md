# Feed Ingestion Pipeline Hardening Handoff

**Date:** 2026-04-09  
**Recommended next branch:** `chi/harden-feed-ingestion-pipeline`  
**Scope:** harden the current per-workspace feed ingestion path into a more reliable, inspectable, and production-usable pipeline without reopening the auth/chat pass.

---

## Purpose

The current system already has real workspace-scoped feed ingestion:

- `run-now` loads configured `FeedSource` rows for one workspace
- fetches each feed URL over HTTP
- parses entries with `feedparser`
- normalizes entries into `ContentItem`
- runs clustering, scoring, shortlist, and report generation

That baseline is useful, but it is still too soft in a few places:

- repeated runs can keep importing overlapping feed entries
- per-feed failure visibility is weak
- feed fetch results are not exposed clearly enough for operations
- ingestion is still feed-entry-centric, not article-body-aware
- QA is not yet strong enough around real redeploy + UI/API inspection

This handoff defines a multi-pass plan to harden that ingestion path.

Do **not** mix unrelated auth/chat/product work into this branch.

---

## Current State

The existing real ingestion path lives primarily in:

- `backend/app/services/pipeline.py`
- `backend/app/services/pipeline_steps.py`
- `backend/app/api/runs.py`
- `backend/app/tasks/pipeline.py`

What it does today:

1. Loads enabled feeds for a workspace.
2. Fetches each feed with `httpx`.
3. Parses feed items with `feedparser`.
4. Normalizes up to 20 entries per feed into `ContentItem`.
5. Persists content items and updates `last_fetched_at`.
6. Continues into cluster / score / shortlist / report generation.

What is intentionally still weak:

1. Duplicate or repeated feed entries are not hardened at ingestion time.
2. Feed failure state is mostly implicit:
   - warning log
   - empty result list
   - no strong per-feed error status progression
3. There is limited fetch/run observability at the feed level.
4. The normalized content mostly reflects feed entry metadata and summary/body snippets, not durable extracted article text.
5. The Web UI does not yet make feed ingestion failure states operationally obvious.

---

## Locked Decisions

These decisions are fixed for this handoff unless explicitly superseded:

- Keep the current workspace-scoped feed model.
- Keep RSS/Atom feed ingestion as the primary source type in this pass.
- Do not build a broad web crawler in this branch.
- Do not add heavyweight new infrastructure unless clearly necessary.
- Keep `run-now` behavior functionally intact while improving reliability.
- Preserve downstream contracts used by clustering, scoring, shortlist, reports, and report chat.
- Fail explicitly on hard ingestion failures; do not silently invent successful fetch results.
- Do not commit data in `data/`.
- Do not commit temporary files in `.ai/tmp/`.

---

## Pass A — Idempotent Content Import

### Goal

Prevent repeated runs from continuously creating duplicate or near-identical `ContentItem` rows from the same feed entries.

### Required Work

1. Define the ingestion-time identity strategy for feed entries.
   - Prefer normalized URL identity first.
   - Use title/source/published fallback only when URL is absent.
2. Reuse the existing dedup logic where appropriate instead of inventing a parallel normalization path.
3. Add a persisted way to detect that an incoming feed entry has already been imported for the same workspace.
4. On repeat runs:
   - skip already-imported entries
   - do not create duplicate `ContentItem` rows
   - keep accurate fetched/imported counts
5. Ensure idempotent behavior does not break report generation or regenerate.

### Suggested Implementation Shape

- Add a small ingestion identity helper in the pipeline layer.
- If needed, add one narrow persisted field or metadata key on `ContentItem` for source-entry identity.
- Keep the write path tightly scoped to ingestion; do not refactor all dedup/clustering logic in this pass.

### Pass A Acceptance Criteria

- Running `POST /api/workspaces/{workspace_id}/run-now` twice in a row against the same unchanged feeds does not double-import the same feed entries.
- Content import count on the second run is reduced to only genuinely new entries, or zero when nothing changed.
- Existing downstream scoring/report generation still succeeds.
- Tests cover repeated-ingestion behavior with fixed feed fixtures.

---

## Pass B — Feed Failure State and Operational Visibility

### Goal

Make feed failures explicit and inspectable rather than just returning an empty list.

### Required Work

1. Define feed fetch outcome states clearly, for example:
   - `healthy`
   - `error`
   - `disabled`
2. On fetch/parse failure:
   - record the failure on the feed
   - capture a short error summary
   - preserve `last_fetched_at` and/or add `last_error_at` as needed
3. On successful later fetch:
   - clear or supersede stale feed error state
4. Add run-event metadata for:
   - feeds attempted
   - feeds succeeded
   - feeds failed
   - entries fetched
   - entries imported
   - entries skipped as already known
5. Keep failure policy explicit:
   - a single feed failure should not necessarily kill the entire workspace run if other feeds can still proceed
   - but the run detail must clearly show partial failure

### Suggested Implementation Shape

- Update feed model/service/API output as needed.
- Add narrow run-event metadata rather than large opaque logs.
- Keep errors short and operationally meaningful.

### Pass B Acceptance Criteria

- A broken feed URL is visible as a feed-level error state after a run.
- A recovered feed returns to a non-error state after a successful fetch.
- Run detail clearly shows partial success/failure at the feed-fetch step.
- The Web UI feed/workspace views expose enough information to understand which feed failed.
- Tests cover both fetch failure and recovery.

---

## Pass C — Better Ingested Content Quality

### Goal

Improve what gets stored for each imported entry so downstream ranking/reporting has better input quality.

### Required Work

1. Keep feed-entry parsing as the base ingest path.
2. Add a bounded article-body enrichment step where practical.
   - only if it can be done with the current toolchain and acceptable complexity
   - do not turn this into a general crawler pass
3. Improve normalization of:
   - title
   - canonical URL
   - author
   - published timestamp
   - summary snippet
   - raw text/body when available
4. Document and cap enrichment behavior:
   - timeout
   - body length cap
   - fallback behavior when article extraction fails
5. Ensure ingestion still remains bounded and deterministic enough for local/dev QA.

### Suggested Implementation Shape

- Keep extraction as an optional enrichment step after feed parse.
- Preserve current feed-entry-only fallback if extraction fails.
- Do not make article-body extraction a hidden hard dependency for the entire run.

### Pass C Acceptance Criteria

- Imported content contains meaningfully better text than raw feed metadata alone when extraction succeeds.
- Extraction failure does not crash the whole pipeline path unexpectedly.
- Timeouts and caps are enforced.
- Tests cover both enriched and fallback cases.

---

## Pass D — UI and API Operability

### Goal

Expose ingestion state clearly enough that an operator can tell what happened without digging through raw logs.

### Required Work

1. Review the existing feed/workspace/run UI surfaces.
2. Add the smallest useful visibility for:
   - feed error state
   - last fetched timestamp
   - last error summary
   - run fetch stats where available
3. Keep UI changes pragmatic and scoped.
4. Do not redesign the application shell.
5. Keep API responses stable where possible; only extend them where needed.

### Suggested Implementation Shape

- Feeds page: status/error visibility.
- Runs detail: feed-fetch counts and partial-failure context.
- Workspace overview: enough signal to notice ingestion problems.

### Pass D Acceptance Criteria

- An operator can identify a broken feed from the Web UI.
- An operator can see that a run partially succeeded even when one feed failed.
- Existing feed create/update/toggle/delete flows still work.
- Existing run detail/report navigation still works.

---

## Pass E — Redeploy and Full QA

### Goal

Validate the hardening work against the real deployed stack, not only local/unit tests.

### Required Commands

Run all of these before handing back:

```bash
make ci
make up
docker compose ps
```

If the app depends on extra runtime configuration for this pass, document the exact command used and the exact environment variables required.

### API QA After `make up`

At minimum verify all of the following:

1. `GET /api/health` returns OK.
2. Login with the configured admin user succeeds.
3. `GET /api/session/me` returns the authenticated user.
4. `POST /api/workspaces/ws-1/run-now` succeeds.
5. The resulting run detail shows fetch-step metadata consistent with the new ingestion accounting.
6. Re-running `run-now` against unchanged feeds does not duplicate already imported entries.
7. A deliberately broken feed shows explicit error behavior in API outputs.
8. A recovered feed returns to a healthy/non-error state after correction.
9. Report generation still succeeds after the ingestion changes.
10. Report thread/source metadata still resolves to valid `ContentItem` IDs.
11. Logout still invalidates the session.

### Web UI QA After `make up`

At minimum verify all of the following:

1. Open the production Web UI.
2. Log in with the configured admin user.
3. Open a workspace with configured feeds.
4. Trigger a run.
5. Confirm the run completes and the UI reflects updated ingestion state.
6. Confirm a healthy feed appears healthy after a successful run.
7. Confirm a broken feed is visibly identifiable from the UI.
8. Confirm a generated report still appears and can be opened.
9. Confirm report thread/source inspection still works after the ingestion changes.
10. Refresh the browser and confirm session restore still works.
11. Logout and confirm protected data is no longer shown.

### Pass E Acceptance Criteria

- `make ci` passes.
- `make up` completes successfully.
- `docker compose ps` shows the expected healthy/running services.
- API QA passes end to end.
- Web UI QA passes end to end.
- No unrelated runtime regressions are introduced in auth, reports, or report chat.

---

## Overall Acceptance Criteria

All of the following must be true before closing this handoff:

1. Feed ingestion remains real and workspace-scoped.
2. Repeated ingestion against unchanged feeds is effectively idempotent.
3. Feed failures are explicit, persisted, and visible through API and UI.
4. Ingested content quality is improved without making the pipeline brittle.
5. Existing downstream report generation still works.
6. Existing report source metadata still resolves correctly.
7. Existing auth/session behavior still works.
8. Existing report chat behavior still works.
9. `make ci` passes.
10. `make up` passes.
11. Deployed API QA passes.
12. Deployed Web UI QA passes.

---

## Non-Goals for This Branch

Do not expand this branch into:

- user management
- report chat redesign
- role-based auth
- broad crawling / search-engine ingestion
- major frontend redesign
- large new infrastructure such as vector databases unless a later handoff explicitly requires it

---

## Delivery Notes

When handing back the completed branch:

1. State exactly which pass(es) were completed.
2. State exactly which commands were run.
3. State whether QA was performed against default `make up` only or with additional runtime configuration.
4. State any remaining known gaps explicitly.
5. Do not claim feed hardening is complete unless all overall acceptance criteria are satisfied.
