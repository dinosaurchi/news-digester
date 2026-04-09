# Backend Integration Repair Handoff

## Goal

Stabilize the current implementation on branch `chi/implement-real-backend` so the backend/frontend integration actually matches the handoff contract before any more remaining Pass 6 or Pass 7 work continues.

This is a repair/stabilization pass, not a new feature pass.

The branch already contains most of Passes 1 through 5.5 and part of Pass 6, but there are still important correctness bugs in the current integration.

Do not continue the remaining Pass 6 or Pass 7 work until the fixes in this handoff are complete, redeployed, and QAed.

---

## Why this handoff exists

The current branch structure is broadly correct:

- real FastAPI backend exists
- frontend no longer uses `src/mock-api`
- backend-served stub session exists
- backend tests pass
- frontend builds

However, several important frontend/backend contract paths are still broken:

1. protected-route session restore is broken
2. regenerate is wired with the wrong identifier
3. source inspection metadata is inconsistent and breaks the source panel
4. sidebar logout does not call backend logout

These are not “later Pass 6/7 quality items”. These are current integration bugs and must be fixed first.

---

## Required scope

Fix all of the following:

1. session restore and protected-route auth gating
2. `/session/me` response handling consistency
3. regenerate contract mismatch
4. source inspection metadata consistency
5. sidebar logout not invalidating backend session
6. automated coverage for the above
7. redeploy with `make up`
8. manual QA of both Web UI and API

After this handoff is complete, the codebase should be in a state where remaining Pass 6 and Pass 7 work can continue safely.

---

## Known issues to fix

## 1. Protected-route session restore is broken

Current problem:

- `src/components/app-layout.tsx` redirects to `/login` immediately when `isLoggedIn` is false
- the async `auth.me()` call runs too late to prevent the redirect on refresh or deep-link
- the frontend should allow an auth hydration/loading phase before deciding whether to redirect

Current files involved:

- `src/components/app-layout.tsx`
- `src/lib/api.ts`
- `src/lib/store.ts`
- `backend/app/api/session.py`
- `backend/app/schemas/session.py`

Required fix:

- introduce an explicit auth hydration state in the frontend store, for example `authStatus: 'unknown' | 'authenticated' | 'anonymous'`
- do not redirect protected routes until the initial `auth.me()` check has completed
- show a lightweight loading/skeleton state while auth is being hydrated
- keep the backend stub session model, but make the frontend routing behavior correct on page refresh and direct navigation

Important:

- the frontend must not create local fake users
- session ownership remains backend-side

---

## 2. `/session/me` contract handling is inconsistent

Current problem:

- login unwraps `{ user }`
- `auth.me()` currently requests `User`
- backend returns `SessionOut` with `{ user: ... }`
- this means session restore shape is wrong even if the route timing bug is fixed

Current files involved:

- `src/lib/api.ts`
- `src/components/app-layout.tsx`
- `backend/app/api/session.py`
- `backend/app/schemas/session.py`

Required fix:

- make `auth.me()` use the same contract as login
- either:
  - keep backend returning `{ user }` and unwrap in frontend consistently, or
  - change both login and me to a direct `User` response

Recommended:

- keep both endpoints returning `{ user }` because login already does
- update frontend `auth.me()` to unwrap `res.user`

Acceptance expectation:

- login, refresh, and deep-link restore the same `User` shape in Zustand

---

## 3. Regenerate is wired with the wrong identifier

Current problem:

- the frontend passes `msg.id` when clicking regenerate from a message bubble
- the backend route is `/api/reports/{report_id}/regenerate`
- backend expects a report/thread identifier, not a message identifier
- this should 404 or behave incorrectly in normal usage

Current files involved:

- `src/pages/ReportThreadPage.tsx`
- `src/lib/api.ts`
- `backend/app/api/reports.py`

Required fix:

- align all layers on one regenerate contract

Choose one implementation and apply it consistently:

1. preserve the current handoff contract:
   - endpoint remains `POST /api/reports/{report_id}/regenerate`
   - frontend calls regenerate with the thread/report id, not the message id
   - UI semantics are updated so the action clearly regenerates the thread/report response

2. or explicitly shift to message-scoped regenerate:
   - backend route becomes message-scoped
   - frontend and tests are updated accordingly
   - only do this if you also update the handoff docs or leave a very explicit note

Recommended:

- preserve the handoff contract and keep regenerate report/thread-scoped

If keeping the current per-message UI affordance:

- either always regenerate the current thread’s latest agent/system response
- or hide/disable regenerate when the clicked bubble is not the regeneratable target

Do not leave a misleading per-message button that silently regenerates something else.

---

## 4. Source inspection metadata is inconsistent and currently broken

Current problem:

- the frontend source panel expects `message.metadata.sources` to contain content item ids
- frontend resolves each source via `/api/content/{id}`
- seeded backend report messages currently store source names
- run-now pipeline currently stores source URLs
- neither shape matches the frontend contract

Current files involved:

- `src/pages/ReportThreadPage.tsx`
- `src/lib/api.ts`
- `backend/app/seed.py`
- `backend/app/api/runs.py`
- `backend/app/tasks/pipeline.py`
- `backend/app/api/content.py`

Required fix:

- standardize `message.metadata.sources` to always contain content item ids
- update seeded report message metadata to use real content ids
- update run-now/pipeline-generated report messages to use real content ids
- ensure linked content items actually exist and are retrievable by `/api/content/{id}`

Recommended additional cleanup:

- where possible, also populate report/content linkage consistently
- keep metadata shape stable and documented

Acceptance expectation:

- opening the Sources panel on seeded threads shows actual content cards
- opening the Sources panel on a newly generated run-now report also shows actual content cards

---

## 5. Sidebar logout does not invalidate the backend session

Current problem:

- header logout calls backend logout
- sidebar logout only clears local Zustand state
- that leaves the backend cookie/session alive
- after refresh, the user can appear logged back in unexpectedly

Current files involved:

- `src/components/header.tsx`
- `src/components/sidebar.tsx`
- `src/lib/api.ts`
- `backend/app/api/session.py`

Required fix:

- make sidebar logout use the same backend logout flow as header logout
- keep local store clearing after backend logout attempt
- keep behavior resilient if logout API fails

Acceptance expectation:

- logout from either header or sidebar invalidates the backend session
- after logout and refresh, `/api/session/me` returns 401 and the app stays at `/login`

---

## 6. Strengthen automated verification

Current issue:

- backend pytest coverage is strong
- frontend test coverage is still too weak and did not catch the integration regressions above

Required additions:

- add frontend tests or integration tests that cover:
  - auth hydration on refresh/deep-link
  - `auth.me()` response unwrapping
  - regenerate using the correct id contract
  - source panel loading real content items from message metadata
  - sidebar logout calling backend logout flow

Backend tests should also cover:

- `/session/me` response shape consistency
- regenerate endpoint behavior for the chosen contract
- seeded and generated message metadata source ids

---

## Implementation guidance

## Auth hydration

Recommended frontend shape:

- add `authStatus` to store:
  - `unknown`
  - `authenticated`
  - `anonymous`

Behavior:

- initial state: `unknown`
- `AppLayout` performs one startup `auth.me()` check
- while `unknown`, render a loading shell, not a redirect
- on success:
  - set `user`
  - set `authStatus = 'authenticated'`
- on failure:
  - clear `user`
  - set `authStatus = 'anonymous'`
- only redirect to `/login` when `authStatus === 'anonymous'`

## Session contract

Recommended:

- keep both `/api/session/login` and `/api/session/me` returning:
  - `{ "user": { ... } }`

Frontend:

- `auth.login()` returns `res.user`
- `auth.me()` also returns `res.user`

## Regenerate

Recommended:

- keep endpoint `POST /api/reports/{report_id}/regenerate`
- change frontend regenerate calls to use `threadId`
- make UI semantics clearly report/thread scoped

## Sources

Required stable contract:

- `ReportMessage.metadata.sources` must be `string[]` of content item ids

Do not store:

- source names
- URLs

Store:

- content item ids only

---

## Files likely to change

Frontend likely:

- `src/lib/api.ts`
- `src/lib/store.ts`
- `src/components/app-layout.tsx`
- `src/pages/LoginPage.tsx`
- `src/pages/ReportThreadPage.tsx`
- `src/components/sidebar.tsx`
- optional new frontend tests

Backend likely:

- `backend/app/api/session.py`
- `backend/app/schemas/session.py`
- `backend/app/api/reports.py`
- `backend/app/api/runs.py`
- `backend/app/tasks/pipeline.py`
- `backend/app/seed.py`
- backend tests covering sessions/reports/runs

---

## Acceptance criteria

All of the following must be true before calling this handoff complete:

1. refreshing a protected route does not bounce the user to `/login` if a valid backend session exists
2. deep-linking directly to a protected route works when a valid backend session exists
3. `auth.me()` and `auth.login()` use a consistent response contract
4. logout from both header and sidebar invalidates the backend session
5. after logout and refresh, the app stays logged out
6. regenerate works end-to-end using one consistent id contract with no 404 caused by identifier mismatch
7. source inspection works for seeded report threads
8. source inspection works for a newly generated run-now report
9. `message.metadata.sources` is consistently content item ids, not names or URLs
10. automated tests cover the repaired auth/regenerate/source/logout paths
11. `make up` completes successfully and the app is usable
12. API QA passes
13. Web UI QA passes

Only after all of the above are true should remaining Pass 6 and Pass 7 work continue.

---

## Required redeploy

After implementing fixes:

```bash
make down
make up
docker compose ps
```

If services fail to start:

- inspect logs with:

```bash
docker compose logs --tail=200 backend
docker compose logs --tail=200 app
docker compose logs --tail=200 db
```

Do not call the task done without a successful `make up` redeploy.

---

## API QA checklist

Use curl or equivalent and verify real responses after `make up`.

## 1. Health

```bash
curl -i http://localhost:8000/api/health
```

Expect:

- HTTP 200
- JSON status payload

## 2. Login

```bash
curl -i -c /tmp/sme.cookies \
  -H 'Content-Type: application/json' \
  -d '{"username":"tester","password":"tester"}' \
  http://localhost:8000/api/session/login
```

Expect:

- HTTP 200
- `Set-Cookie` for `session_id`
- body with `{ "user": { "id", "username", "displayName", "role" } }`

## 3. Session restore

```bash
curl -i -b /tmp/sme.cookies http://localhost:8000/api/session/me
```

Expect:

- HTTP 200
- same stable user shape

## 4. Logout

```bash
curl -i -b /tmp/sme.cookies -c /tmp/sme.cookies \
  -X POST http://localhost:8000/api/session/logout
curl -i -b /tmp/sme.cookies http://localhost:8000/api/session/me
```

Expect:

- logout returns success
- subsequent `/session/me` returns 401

## 5. Reports and messages

Use one seeded workspace/thread and verify:

```bash
curl -s http://localhost:8000/api/workspaces/ws-1/reports
curl -s http://localhost:8000/api/report-threads/<thread-id>
curl -s http://localhost:8000/api/report-threads/<thread-id>/messages
```

Expect:

- messages contain stable DTOs
- source metadata shape is consistent

## 6. Regenerate

Call the actual chosen regenerate endpoint/contract and verify:

- no 404 caused by mismatched identifier
- response returns updated message/report payload
- thread messages reflect the regenerate result afterward

## 7. Run now

```bash
curl -i -X POST http://localhost:8000/api/workspaces/ws-1/run-now
```

Then inspect:

```bash
curl -s http://localhost:8000/api/workspaces/ws-1/runs
curl -s http://localhost:8000/api/workspaces/ws-1/reports
```

Expect:

- run created successfully
- report created successfully
- report thread message metadata sources point to content item ids

---

## Web UI QA checklist

After `make up`, verify manually in the browser.

Base URLs:

- frontend: `http://localhost:3000`
- backend docs: `http://localhost:8000/api/docs`

## 1. Login flow

- open `/login`
- sign in with non-empty credentials
- confirm login succeeds
- confirm user name appears in header/sidebar

## 2. Refresh persistence

- navigate to `/workspaces/ws-1`
- refresh the browser
- confirm you remain in the app and are not redirected to `/login`

## 3. Deep-link persistence

- with valid session, open `/workspaces/ws-1/reports/th-1` directly in a new tab
- confirm the page loads without redirect loop

## 4. Header logout

- logout from the header menu
- confirm redirect to `/login`
- refresh browser
- confirm you remain logged out

## 5. Sidebar logout

- log in again
- logout from the sidebar
- confirm redirect to `/login`
- refresh browser
- confirm you remain logged out

## 6. Seeded report source inspection

- log in
- open a seeded report thread
- click source inspection on a message that has sources
- confirm the sources panel shows real content cards, not empty state

## 7. Regenerate

- from a report thread, trigger regenerate using the chosen UI semantics
- confirm the action succeeds
- confirm no 404 or silent no-op
- confirm the thread updates with regenerated content

## 8. Run now + generated report

- trigger `Run Now` from a workspace
- wait for the run/report flow to complete
- open the generated report thread
- confirm source inspection works there too

---

## Deliverables for this repair handoff

Produce:

1. code fixes for the auth/regenerate/source/logout issues
2. automated tests covering those repaired paths
3. successful redeploy with `make up`
4. written QA notes summarizing API QA and Web UI QA
5. a short follow-up note stating whether the branch is now safe to resume remaining Pass 6 and Pass 7 work

---

## Out of scope for this handoff

Do not expand into the remaining Pass 6 and Pass 7 feature work yet, except for the minimum code changes required to repair the broken integration paths above.

Examples out of scope here:

- real LLM reasoning integration
- full dedup/clustering system
- meaningful embeddings/BM25 ranking
- richer autonomous report generation quality work

Those come after this stabilization handoff is complete.

---

## Exit condition

This handoff is complete only when:

- code fixes are merged locally
- tests pass
- `make up` redeploy succeeds
- API QA passes
- Web UI QA passes
- the branch is safe to continue with the remaining Pass 6 and Pass 7 work
