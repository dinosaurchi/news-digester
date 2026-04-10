# Feed Ingestion Pipeline Follow-Up Handoff

**Date:** 2026-04-10  
**Recommended branch base:** `main` after merging the current feed-ingestion work, or continue on `chi/harden-feed-ingestion-pipeline` if that branch remains open  
**Primary target:** close the remaining correctness and verification gaps found during review of `chi/harden-feed-ingestion-pipeline`

---

## Why this handoff exists

The branch `chi/harden-feed-ingestion-pipeline` implements most of the original hardening plan, but it should not be treated as fully complete yet.

The review found three concrete implementation gaps and one delivery gap:

1. ingestion-time dedup still allows duplicates that appear more than once in the same fetched batch
2. `POST /api/feeds/{feed_id}/test` does not maintain feed error timestamps and fetch timestamps consistently with the main pipeline path
3. `source_entry_id` stores normalized URLs in a column sized too narrowly for that strategy
4. the redeploy and end-to-end QA pass was not demonstrated as completed

This follow-up handoff is narrowly scoped to close those gaps and finish the hardening work properly.

Do **not** expand this branch into unrelated auth/chat/product work.

---

## Locked decisions

These decisions stay fixed for this follow-up unless explicitly superseded:

- keep the current workspace-scoped RSS/Atom ingestion model
- keep `run-now` behavior functionally intact
- do not redesign the application shell
- do not build a general crawler in this pass
- keep the fix set tight and operational
- do not commit `data/`
- do not commit `.ai/tmp/`
- `make ci` must pass before handoff completion
- handoff completion requires redeploy and real stack QA, not only unit tests

---

## Pass 1 - Fix ingestion-time dedup correctness

### Goal

Make ingestion effectively idempotent both across repeated runs and within a single fetched batch.

### Required work

1. Update the ingestion path in `backend/app/services/pipeline_steps.py` so duplicate entries in the same `raw_items` batch are skipped after the first accepted item.
2. Preserve the existing identity strategy:
   - normalized canonical URL first
   - title/source/published fallback only when URL is absent
3. Keep fetched/imported/skipped counts accurate.
4. Keep downstream clustering, scoring, shortlist, report generation, and regenerate behavior intact.

### Implementation notes

- The current code preloads already-imported `source_entry_id` values from the DB, but it should also update the in-memory seen set as each new item is accepted in the current batch.
- Do not weaken the fallback identity strategy to avoid this bug.

### Pass 1 acceptance criteria

- Two identical or canonical-equivalent entries in the same fetched batch produce only one new `ContentItem`.
- Running `run-now` repeatedly against unchanged feeds does not create duplicate `ContentItem` rows.
- `entries_imported` and `entries_skipped` remain accurate in run metadata.
- Backend tests cover:
  - repeated ingestion across runs
  - duplicate entries inside the same batch
  - mixed batch containing both new and already-known entries

---

## Pass 2 - Fix feed status consistency for `/feeds/{id}/test`

### Goal

Make feed validation state consistent whether the operator uses the test endpoint or the full pipeline run.

### Required work

1. Review `backend/app/api/feeds.py` and align `POST /api/feeds/{feed_id}/test` with the intended feed-state rules.
2. On test failure:
   - mark the feed as `error`
   - set `last_error`
   - set `last_error_at`
   - do not falsely advance `last_fetched_at` if the intended semantics are "successful fetch only"
3. On test success:
   - mark the feed as `healthy`
   - clear stale error fields
   - update `last_fetched_at`
4. Keep the response payload and UI expectations coherent with those semantics.

### Implementation notes

- The operator should not see one state model after `run-now` and a different one after using the feed test button.
- Keep the state transitions explicit and symmetric.

### Pass 2 acceptance criteria

- A failed feed test leaves the feed in explicit error state with `lastError` and `lastErrorAt`.
- A later successful feed test clears the error state and updates `lastFetchedAt`.
- Feed state shown by the API is consistent with feed state shown in the Web UI.
- Backend tests cover both failure and recovery on `/api/feeds/{feed_id}/test`.

---

## Pass 3 - Harden `source_entry_id` storage

### Goal

Make the persisted ingestion identity safe for real canonical URLs and durable enough for the dedup strategy already chosen.

### Required work

1. Review the storage shape for `ContentItem.source_entry_id`.
2. Fix the mismatch between:
   - storing full normalized URLs as the preferred identity
   - limiting the column to a short string length
3. Choose one consistent approach and implement it fully:
   - widen the column enough for normalized URLs, or
   - store a durable hashed identity while preserving the same logical identity strategy
4. Ensure existing migration behavior is handled correctly for local/dev databases.
5. Keep idempotency behavior stable after the schema change.

### Implementation notes

- This is a correctness issue first, not just a schema cleanup.
- If you move to a hashed persisted key, keep the URL-first identity semantics logically intact.
- Avoid introducing a large migration chain for a narrow fix.

### Pass 3 acceptance criteria

- Long canonical article URLs no longer risk breaking content import.
- `source_entry_id` remains deterministic and stable for the same feed entry.
- Existing idempotency tests still pass.
- Add at least one test covering a long URL or equivalent persistence edge case.

---

## Pass 4 - Add targeted QA helpers

### Goal

Make the final redeploy QA repeatable enough that operators can re-run it without rebuilding the checklist from scratch.

### Required work

1. Add concise manual QA documentation for the exact API and Web UI checks to run after deploy.
2. If useful, add Playwright-based manual QA tests under `tests/manual/`.
3. Any tests added under `tests/manual/` must:
   - be clearly marked as manual or non-CI
   - not run from `make ci`
   - be usable against the deployed local stack after `make up`
4. Keep these tests pragmatic:
   - login
   - trigger run
   - inspect feed error/healthy state
   - inspect run detail metadata
   - open generated report and sources

### Implementation notes

- These tests are optional, but recommended if they materially improve repeatability.
- Do not build a second full CI suite under `tests/manual/`.

### Pass 4 acceptance criteria

- There is a clear, repo-local QA procedure for post-deploy verification.
- If manual Playwright tests are added, they run outside `make ci` and cover the intended QA path.
- The QA helper artifacts match the actual current routes, auth flow, and runtime behavior.

---

## Pass 5 - Seeded end-to-end workspace/run coverage

### Goal

Prove that a brand-new workspace can be created, seeded with feeds, ingested, and turned into a report without depending on pre-existing manual data setup.

### Required work

1. Add an end-to-end backend coverage path that:
   - creates a new workspace
   - creates a small predefined set of feeds for that workspace
   - fetches/imports related content
   - triggers `run-now`
   - verifies report generation and source linkage
2. Keep automated coverage deterministic:
   - prefer local RSS fixtures, mocked HTTP responses, or controlled test fixtures
   - do not rely on live public feeds in CI-facing tests
3. For manual deployed QA, define a small curated real-feed set that can be added to a new workspace after `make up`.
4. Ensure the seeded run path exercises the real ingestion/report pipeline, not a side-channel shortcut.

### Implementation notes

- This pass is intended to remove hidden dependence on pre-existing `ws-1` state for meaningful QA.
- Automated tests should use deterministic feed fixtures.
- Real public feeds are acceptable for manual QA only, because they are temporally unstable.

### Suggested shape

- Add one backend integration test that:
  - creates a workspace
  - creates 2-3 feed records
  - returns related feed entries through fixture/mocked HTTP fetches
  - calls `POST /api/workspaces/{workspace_id}/run-now`
  - asserts:
    - content items were imported
    - fetch metadata was recorded
    - a report was created
    - report sources resolve to valid `ContentItem` rows
- Optionally add a manual helper under `tests/manual/` or docs that creates a fresh workspace and seeds a curated real-feed set after deploy.

### Pass 5 acceptance criteria

- There is automated coverage for the create-workspace -> add-feeds -> run pipeline -> generate report path using deterministic fixtures.
- The automated seeded flow does not require pre-existing manual workspace/feed setup.
- The seeded flow verifies generated report/source integrity, not only content import.
- Manual QA docs include a clear fresh-workspace flow with a predefined real-feed set for deployed validation.

---

## Pass 6 - Redeploy and full-stack QA

### Goal

Prove the fixed branch works on the actual deployed local stack, not only in backend/frontend test runners.

### Required commands

Run all of the following and do not hand back the work without them succeeding:

```bash
make ci
make up
docker compose ps
```

If extra runtime configuration is required, state the exact command and exact environment variables used.

### API QA after `make up`

At minimum verify all of the following against the running stack:

1. `GET /api/health` returns OK.
2. Login with the configured admin user succeeds.
3. `GET /api/session/me` returns the authenticated user.
4. Create a fresh workspace if needed for QA, or clearly state which existing workspace is used.
5. Add a predefined feed set to the workspace under test.
6. `POST /api/workspaces/{workspace_id}/run-now` succeeds.
7. The run imports content and produces a report from those configured feeds.
8. Run detail shows fetch-step metadata with accurate:
   - feeds attempted
   - feeds succeeded
   - feeds failed
   - entries fetched
   - entries imported
   - entries skipped
9. Re-running `run-now` against unchanged feeds does not create duplicate imports.
10. A deliberately broken feed appears as explicit error state in API output.
11. A recovered feed returns to healthy state after correction.
12. Generated report creation still succeeds.
13. Report source metadata still resolves to valid `ContentItem` records.
14. Logout invalidates the session.

### Web UI QA after `make up`

At minimum verify all of the following against the running stack:

1. Open the production Web UI.
2. Log in successfully.
3. Create a fresh workspace if needed, or clearly state which workspace is used.
4. Add the predefined QA feed set if it is not already present.
5. Trigger a run.
6. Confirm the run completes and the UI shows updated ingestion state.
7. Confirm imported content/report output appears for that workspace.
8. Confirm a healthy feed is visibly healthy after a successful run.
9. Confirm a broken feed is visibly identifiable from the UI.
10. Confirm a recovered feed returns to a non-error display state.
11. Open the run detail view and confirm fetch-step metadata is visible and coherent.
12. Open the generated report.
13. Open report sources and confirm they still resolve correctly.
14. Refresh the browser and confirm session restore still works.
15. Logout and confirm protected data is no longer shown.

### Optional manual Playwright QA

If helpful, add Playwright-based manual QA coverage in `tests/manual/`, for example:

- `tests/manual/feed-ingestion-qa.spec.ts`
- `tests/manual/README.md`

Recommended coverage:

1. login
2. navigate to workspace
3. trigger run
4. observe run completion
5. confirm feed status/error indicators
6. open run detail and report views
7. verify session restore and logout

These tests must remain outside the `make ci` path.

### Pass 6 acceptance criteria

- `make ci` passes.
- `make up` completes successfully.
- `docker compose ps` shows the expected healthy/running services.
- API QA passes end to end.
- Web UI QA passes end to end.
- If manual Playwright tests were added, they execute successfully against the deployed local stack.
- No unrelated runtime regressions are introduced in auth, reports, or report chat.

---

## Overall acceptance criteria

Do not call this handoff complete unless all of the following are true:

1. feed ingestion remains workspace-scoped and real
2. ingestion is effectively idempotent across repeated runs and within the same fetched batch
3. feed failure state is explicit, persisted, and consistent across pipeline runs and feed-test actions
4. `source_entry_id` storage is safe for the chosen identity strategy
5. ingested content quality improvements remain intact
6. a fresh workspace can be created, seeded with predefined feeds, and taken through ingestion to report generation
7. existing downstream report generation still works
8. existing report source metadata still resolves correctly
9. auth/session behavior still works
10. report chat behavior still works
11. `make ci` passes
12. `make up` passes
13. deployed API QA passes
14. deployed Web UI QA passes
15. any manual Playwright QA added under `tests/manual/` is clearly outside CI and usable
16. remaining known gaps, if any, are stated explicitly rather than implied away

---

## Out of scope

Do not expand this follow-up into:

- user management changes
- report chat redesign
- new provider integrations
- broad crawling/search ingestion
- major frontend redesign
- large infrastructure additions

---

## Delivery requirements

When handing back the completed work:

1. list which pass(es) were completed
2. list the exact commands run
3. state whether QA used default `make up` or extra runtime configuration
4. state whether manual Playwright tests were added under `tests/manual/`
5. state any remaining gaps explicitly
6. do not claim completion unless all overall acceptance criteria are satisfied
