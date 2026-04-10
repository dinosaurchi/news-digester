# Feed Ingestion Pipeline Follow-Up Completion Note

**Date:** 2026-04-10  
**Branch:** `chi/harden-feed-ingestion-pipeline`

This note records the concrete verification performed to close the follow-up handoff in [2026-04-10_feed_ingestion_pipeline_followup_handoff.md](/workspace/projects/sme-news-admin/docs/2026-04-10_feed_ingestion_pipeline_followup_handoff.md).

## Completed passes

- Pass 1 - Fix ingestion-time dedup correctness
- Pass 2 - Fix feed status consistency for `/feeds/{id}/test`
- Pass 3 - Harden `source_entry_id` storage
- Pass 4 - Add targeted QA helpers
- Pass 5 - Seeded end-to-end workspace/run coverage
- Pass 6 - Redeploy and full-stack QA

## Commands run

```bash
make ci
make up
docker compose ps
docker compose exec -T backend python - <<'PY'
# in-container proxy/API/Web UI route QA via http://app
PY
```

## Notes about runtime environment

- Default `make up` stack was used.
- This runner could not connect to host-published `localhost:3000`, so deployed QA was executed from inside the running `backend` container over the compose network against `http://app`.
- That still exercised the nginx-served Web UI routes and proxied `/api/*` endpoints.
- No manual Playwright tests were added in this pass.

## `make ci`

- Passed
- Frontend lint/typecheck/tests/build passed
- Backend test suite passed: `498 passed`

## `make up`

- Passed
- Containers rebuilt and started successfully

## `docker compose ps`

Observed healthy/running services:

- `app`
- `backend`
- `worker`
- `beat`
- `db`
- `redis`
- `opencode-server`
- `opencode-agent-adapter`

## API QA results

QA was executed through nginx proxy at `http://app/api`.

Verified:

1. `GET /api/health` returned OK
2. login with `admin` / `admin` succeeded
3. `GET /api/session/me` returned the authenticated user
4. a fresh workspace was created
5. predefined feeds were added:
   - `https://hnrss.org/frontpage`
   - `https://hnrss.org/newest`
   - `http://feeds.bbci.co.uk/news/technology/rss.xml`
6. `POST /api/feeds/{id}/test` succeeded for a healthy feed
7. first `POST /api/workspaces/{workspace_id}/run-now` succeeded
8. first run fetch metadata showed:
   - `feedsAttempted: 3`
   - `feedsSucceeded: 3`
   - `feedsFailed: 0`
   - `entriesFetched: 60`
   - `entriesImported: 60`
9. generated report existed and was `published`
10. report thread system message contained source metadata
11. all report source IDs resolved through `GET /api/content/{id}`
12. second `run-now` succeeded and was idempotent:
   - `entriesImported: 0`
   - `entriesSkipped: 60`
13. a deliberately broken feed failed with explicit error state:
   - `success: false`
   - non-null `lastError`
   - non-null `lastErrorAt`
   - `lastFetchedAt: null`
14. after fixing the broken feed URL and retesting, the feed recovered to:
   - `status: healthy`
   - `lastError: null`
   - `lastErrorAt: null`
   - non-null `lastFetchedAt`
15. logout invalidated the session and `/api/session/me` returned `401`

Live QA identifiers from the run:

- workspace: `266cb5959de748b8ae8beb115b2b7265`
- first run: `638b6295dfcc4e619a91037773a04828`
- second run: `59eda3774f0b42b09b75f6b16fe6bd4c`
- report: `f659a572eda14b9aaa8b35ed6e283a7b`

## Web UI route QA results

Because a real browser was not available in this runner, Web UI verification was performed by fetching nginx-served SPA routes and confirming they returned the application shell HTML successfully.

Verified routes:

- `/login`
- `/workspaces/266cb5959de748b8ae8beb115b2b7265`
- `/workspaces/266cb5959de748b8ae8beb115b2b7265/feeds`
- `/workspaces/266cb5959de748b8ae8beb115b2b7265/runs`
- `/workspaces/266cb5959de748b8ae8beb115b2b7265/reports/f659a572eda14b9aaa8b35ed6e283a7b`

For each route:

- HTTP 200 returned
- SPA root container was present
- built asset references were present

## Remaining known gaps

- No browser-automation pass was run in this completion note.
- Web UI verification here confirms route serving and proxy correctness, not interactive client-side rendering in a headless browser.
