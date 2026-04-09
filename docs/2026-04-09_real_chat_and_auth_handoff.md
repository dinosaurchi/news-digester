# Real Report Chat and Real Auth Handoff

**Date:** 2026-04-09
**Branch context:** created after Pass-7 backend stabilization.
**Scope:** remove the remaining backend report-chat mock response and minimal stub auth.

---

## Current State

The frontend is wired to backend APIs; there is no runtime mock API in the frontend.

Two backend behaviors are still intentionally lightweight:

1. `POST /api/report-threads/{thread_id}/messages`
   - Current behavior: persists the user message, then creates a hardcoded `agent` thank-you message with `metadata.model = "mock-agent"`.
   - File: `backend/app/api/reports.py`

2. `POST /api/session/login`
   - Current behavior: accepts any non-empty username/password and creates a backend session.
   - Files: `backend/app/api/session.py`, `backend/app/services/session.py`

Do **not** hide this by renaming it. Replace it with a real implementation or make the unavailable capability explicit.

---

## Pass A — Real Report Chat

### Locked Product Decisions

- Report chat **requires OpenCode**.
- If `OPENCODE_ENABLED=false`, report chat must return explicit HTTP 503. Do not create an `agent` message.
- Chat context is the **current report plus that report's source content only**.
- On assistant/provider failure, persist the user's message, return explicit failure, and do **not** create fake/error `agent` messages.
- Do not return a fake acknowledgement.
- Do not use all workspace content history in this pass.

### Backend Approach

1. In `backend/app/api/reports.py`, replace the hardcoded agent-message block in `send_message()`.
2. Persist the user message first.
3. Load the report by `thread_id`.
4. Load ordered thread messages for recent context.
5. Load source `ContentItem` records from the latest generated report message metadata:
   - Prefer current report message `metadata.sources`.
   - Fall back to `report.metadata_json.sources`.
   - Keep source order.
   - Cap context size to a documented small value unless a summarization strategy exists.
6. Generate the reply through a backend service function, for example `app.services.report_chat.generate_report_chat_reply(...)`.
7. If `settings.OPENCODE_ENABLED == false`, commit the user message, then return HTTP 503 with message `Report chat assistant is not configured`.
8. If `settings.OPENCODE_ENABLED == true`, call `OpenCodeClient` through a dedicated chat/report-QA method.
9. Do **not** silently fall back from failed OpenCode to a template answer.
10. On any OpenCode/provider failure, keep the user message committed and return an explicit error response. Do not create an `agent` message.
11. Create the `agent` message only after a real assistant response exists.
12. Store useful metadata:
    - `model`
    - `sources`
    - `opencodeSessionId` when available
    - token/usage data when available

### Frontend Approach

1. Keep the current chatbox flow in `src/pages/ReportThreadPage.tsx`.
2. On HTTP 503 / assistant-not-configured, show a visible error toast or inline failed pending state.
3. Do not append a fake agent response in the frontend.
4. Keep thumbs and source-inspection behavior working on real assistant messages.

### Report Chat Acceptance Criteria

- `rg -n "mock-agent|Thank you for your feedback|mocked agent|Create mocked agent response" backend/app src` has no runtime matches.
- With `OPENCODE_ENABLED=false`, posting a chat message persists the user message and fails explicitly without creating an agent reply.
- With `OPENCODE_ENABLED=true` and a working adapter/provider, posting a chat message creates one real `agent` message that answers using report/source context.
- The response metadata contains the model/provider identity.
- If the provider/adapter fails, the request fails explicitly and no successful fake agent message is created.
- Existing thumbs up/down endpoints still work.
- Existing message feedback events still work.
- Existing report generation and regenerate still work.

---

## Pass B — Real Auth

### Locked Product Decisions

- Replace accept-any-credentials auth with a real user identity store.
- Keep cookie-based session behavior.
- Bootstrap an admin user via environment/dev seed path.
- Do not implement user CRUD, invites, or password reset in this pass.
- Keep `role` in the User DTO/session, but treat it as informational only. Do not add endpoint-level permission enforcement in this pass.

### Backend Approach

1. Add a database model/migration for users, for example:
   - `users.id`
   - `users.username` unique
   - `users.password_hash`
   - `users.display_name`
   - `users.role`
   - `users.status`
   - timestamps
2. Hash passwords with a maintained password hashing library.
3. Seed/dev-bootstrap exactly one admin user via environment and/or the existing dev seed path. Document the exact mechanism in `.env.example` and the final PR/commit note.
4. Update `backend/app/api/session.py`:
   - Validate username/password against stored hash.
   - Return 401 for wrong username/password.
   - Keep `/session/me` DTO stable for the frontend.
   - Keep `/session/logout`.
5. Update `backend/app/services/session.py`:
   - Store session-to-user identity, not just arbitrary submitted username.
   - Keep server-side session deletion.
6. Add env documentation in `.env.example`.
7. Add tests for success, bad password, unknown user, disabled user, me/logout.
8. Do not add user management endpoints in this pass.
9. Do not add role-based authorization checks in this pass.

### Frontend Approach

1. Keep existing login form and `api.auth.login(username, password)`.
2. Display existing login error on HTTP 401.
3. Do not embed demo credentials in runtime UI.

### Auth Acceptance Criteria

- `rg -n "Accept any non-empty|mock user|stub session" backend/app src` has no runtime matches.
- Login with wrong password returns 401.
- Login with unknown user returns 401.
- Login with valid seeded/dev user returns the existing User DTO.
- `/api/session/me` returns the same user after login cookie is set.
- `/api/session/logout` invalidates the session.
- Frontend login works through the backend; no frontend auth mock.

---

## Required Verification

Run all of these before handing back:

```bash
make ci
make up
docker compose ps
```

API QA after `make up`:

1. `GET /api/health` returns OK.
2. Login success with a real configured user.
3. Login failure with wrong password returns 401.
4. `GET /api/session/me` returns authenticated user.
5. `POST /api/workspaces/ws-1/run-now` succeeds in default deterministic mode.
6. New report exists and has source-backed system message.
7. Report chat with default `OPENCODE_ENABLED=false`: user message is persisted, request returns explicit HTTP 503, and no `agent` message is created.
8. Report chat with `OPENCODE_ENABLED=true` and working OpenCode/provider: configured path creates a real agent response grounded in current report/source context.
9. Regenerate still appends a same-thread system message and preserves source IDs.
10. Logout invalidates the session.

Web UI QA after `make up`:

1. Open the production Web UI.
2. Log in with a real configured user.
3. Open a workspace.
4. Trigger/view a report.
5. Use report chat and verify either a real response or a clear configured/unconfigured error.
6. Thumb up/down still persists.
7. Refresh browser and confirm session restore.
8. Logout and verify protected routes no longer show data.

Do not commit data in `data/`.
Do not commit temporary files in `.ai/tmp/`.
