# Delete UI — Workspaces, Content & Reports Handoff

**Date:** 2026-04-12
**Recommended branch base:** current `main` / HEAD of this repository
**Primary target:** surface delete actions for workspaces, content items, and reports in the Web UI, backed by complete API endpoints where missing

---

## Why this handoff exists

The Web UI currently offers no way to delete workspaces, content items, or reports.
Users must resort to direct database access or raw API calls to remove stale data.
This handoff adds the missing endpoints and wires up delete actions in every relevant page,
following the established pattern from `FeedsPage`.

Current state confirmed from repository:

- **Workspace delete** — backend endpoint `DELETE /workspaces/{workspace_id}` exists
  (`backend/app/api/workspaces.py:155`) and performs a soft-delete (`status → archived`),
  but no UI triggers it. `api.ts:38` already has `workspaces.archive()` but it is never called.
- **Content item delete** — no backend endpoint and no service-layer method exist.
- **Report delete** — no backend endpoint and no service-layer method exist.
- **Confirmation pattern** — `FeedsPage.tsx` has a complete, reusable modal-confirmation
  pattern (state-based backdrop dialog) that must be replicated, not reinvented.

---

## Locked decisions

- Workspace delete remains a **soft-delete** (`status = "archived"`).
  The existing backend method is not changed. Archived workspaces must not appear
  in the workspace list (`GET /workspaces` already filters by `status = "active"`).
- Content item delete is a **hard delete** from the database. Content items are
  transient pipeline outputs — no soft-delete column exists or will be added.
- Report delete is a **hard delete**. `Report.messages` already has
  `cascade="all, delete-orphan"` so child messages are removed automatically.
- No new database migrations are required for any pass.
- Confirmation dialogs follow the exact visual pattern in `FeedsPage.tsx:422-452`
  (modal with backdrop blur, AlertCircle icon, Cancel + Delete buttons, spinner
  during pending mutation). Do not introduce a different pattern.
- All frontend API calls go through `src/lib/api.ts` (add methods there first,
  then use them in pages).
- `make ci` must pass before a pass is considered complete.
- Each pass ends with `make up` redeploy and manual Web UI + API verification.

---

## Reference: established delete pattern

Before starting, read and understand these files in full:

| File | Purpose |
|------|---------|
| `src/pages/FeedsPage.tsx:51,86-94,317-323,422-452` | Complete frontend delete flow |
| `backend/app/api/feeds.py:87-94` | Backend route handler |
| `backend/app/services/feed.py:57-65` | Service-layer soft-delete |
| `src/lib/api.ts:57-58` | Frontend API method for feeds delete |
| `src/lib/api-client.ts:41-50` | Generic `delete<T>` helper |

Key points:
- State variable `deleteConfirmId: string | null` controls which item is pending confirmation.
- The mutation calls the API, then on success calls `queryClient.invalidateQueries` to refresh
  the list and resets `deleteConfirmId` to `null`.
- The confirmation modal renders at the bottom of the JSX tree, conditionally when
  `deleteConfirmId !== null`.
- The delete button in the row/card is separate from the confirmation — clicking it only
  sets `deleteConfirmId`, it does not call the API directly.

---

## Pass 1 — Wire up workspace delete in the UI

### Goal

Let users archive (soft-delete) a workspace from the workspaces list page.
The workspace must disappear from the list immediately after deletion.

### Required work

**Frontend only** (backend endpoint already exists):

1. In `src/lib/api.ts`, confirm `workspaces.archive(id)` is already present at line 38.
   If the return type is `Workspace`, change it to `void` to match the backend 204 response.
   If it is already `void`, leave it unchanged.

2. In `src/pages/WorkspacesPage.tsx`:
   a. Add `deleteConfirmId` state (`string | null`, initialised to `null`).
   b. Add a `deleteMutation` using `useMutation` that calls `api.workspaces.archive(id)`,
      invalidates the `['workspaces']` query on success, and resets `deleteConfirmId` to `null`.
   c. Add a delete button to each workspace card (trash icon, red-on-hover, positioned in the
      card's top-right corner or footer action row — whichever fits the existing card layout
      without rearranging unrelated elements).
   d. Add the confirmation modal at the bottom of the JSX tree, following the pattern from
      `FeedsPage.tsx:422-452` verbatim in structure. The warning copy must read:
      *"This will permanently archive the workspace and all its data. This action cannot be undone."*
   e. Do not modify any other behaviour of the workspaces page.

### Files to modify

- `src/lib/api.ts` (return-type check only)
- `src/pages/WorkspacesPage.tsx`

### Acceptance criteria

- [ ] Workspace cards each have a delete/archive button.
- [ ] Clicking the button opens a confirmation modal with the required copy.
- [ ] Cancelling the modal closes it without any side-effect.
- [ ] Confirming calls `DELETE /workspaces/{id}`, the modal shows a spinner during the call,
      and the card disappears from the list on success.
- [ ] Navigating to an archived workspace URL shows a 404/not-found state (existing behaviour).
- [ ] `make ci` passes.
- [ ] `make up` redeploy succeeds and the above behaviour is verified in the browser.

---

## Pass 2 — Backend: content item delete endpoint

### Goal

Add `DELETE /content/{content_item_id}` to the backend so the UI (Pass 3) can call it.

### Required work

1. **Service layer** — in `backend/app/services/content.py`, add:
   ```python
   def delete_content_item(db: Session, item_id: str) -> None:
       item = db.get(ContentItem, item_id)
       if item is None:
           raise NotFoundError(f"Content item {item_id} not found")
       db.delete(item)
       db.commit()
   ```
   Use the same `NotFoundError` (or `HTTPException 404`) pattern used elsewhere in the service layer.

2. **Router** — in `backend/app/api/content.py`, add:
   ```
   DELETE /content/{content_item_id}
   ```
   - Requires authentication (same `get_current_user` dependency used on all other routes).
   - Calls the service method.
   - Returns `204 No Content` on success.
   - Returns `404` if the item does not exist.
   - No workspace membership check is needed beyond authentication (consistent with the
     existing `GET /content/{content_item_id}` at line 65 which has no workspace guard).

3. **No migration required** — `ContentItem` is hard-deleted; no status column is added.

### Files to modify

- `backend/app/services/content.py`
- `backend/app/api/content.py`

### Acceptance criteria

- [ ] `DELETE /content/{id}` with a valid authenticated session returns `204`.
- [ ] The row is gone from the database after the call.
- [ ] `DELETE /content/{id}` with a non-existent id returns `404`.
- [ ] `DELETE /content/{id}` without authentication returns `401`.
- [ ] `make ci` passes (add tests in `backend/tests/` following the existing test patterns).
- [ ] `make up` redeploy succeeds and the endpoint is smoke-tested with curl or the test script.

---

## Pass 3 — Wire up content item delete in the UI

### Goal

Let users delete individual content items from the content page.

### Required work

1. In `src/lib/api.ts`, add inside the `content` namespace:
   ```ts
   delete: (itemId: string) => apiClient.delete<void>(`/content/${itemId}`).then(() => true),
   ```

2. In `src/pages/ContentPage.tsx`:
   a. Add `deleteConfirmId` state (`string | null`, initialised to `null`).
   b. Add a `deleteMutation` that calls `api.content.delete(id)`, invalidates the content
      query for the current workspace on success, and resets `deleteConfirmId`.
   c. Add a delete button to each content row. The button should be a small trash icon placed
      at the end of the row's action column (or alongside the existing row detail trigger).
      Do not break the existing sort/filter/detail-sheet behaviour.
   d. Add the confirmation modal following the `FeedsPage` pattern. Copy:
      *"This will permanently delete this content item. This action cannot be undone."*

3. When the detail sheet (`ContentDetailSheet` or inline panel) is open for the item being
   deleted, close it as part of the mutation's `onSuccess` handler.

### Files to modify

- `src/lib/api.ts`
- `src/pages/ContentPage.tsx`

### Acceptance criteria

- [ ] Each content row has a delete button.
- [ ] Clicking opens the confirmation modal with the required copy.
- [ ] Cancel closes the modal with no change.
- [ ] Confirm calls `DELETE /content/{id}`, shows a spinner, and removes the row on success.
- [ ] If the detail sheet for that item is open, it closes on deletion.
- [ ] No other content rows are affected.
- [ ] `make ci` passes.
- [ ] `make up` redeploy succeeds and the behaviour is verified in the browser.

---

## Pass 4 — Backend: report delete endpoint

### Goal

Add `DELETE /reports/{report_id}` to the backend so the UI (Pass 5) can call it.

### Required work

1. **Service layer** — in `backend/app/services/report.py` (or whichever file owns report
   CRUD), add:
   ```python
   def delete_report(db: Session, report_id: str) -> None:
       report = db.get(Report, report_id)
       if report is None:
           raise NotFoundError(f"Report {report_id} not found")
       db.delete(report)
       db.commit()
   ```
   `Report.messages` has `cascade="all, delete-orphan"` so all child `ReportMessage` rows
   are deleted automatically. No manual child deletion is needed.

2. **Router** — in `backend/app/api/reports.py`, add:
   ```
   DELETE /reports/{report_id}
   ```
   - Requires authentication.
   - Calls the service method.
   - Returns `204 No Content` on success.
   - Returns `404` if not found.

3. **No migration required.**

### Files to modify

- `backend/app/services/report.py` (or equivalent report service file)
- `backend/app/api/reports.py`

### Acceptance criteria

- [ ] `DELETE /reports/{id}` with a valid session returns `204`.
- [ ] The report and all its `ReportMessage` children are gone from the database.
- [ ] `DELETE /reports/{id}` with a non-existent id returns `404`.
- [ ] `DELETE /reports/{id}` without authentication returns `401`.
- [ ] `make ci` passes (add tests following existing patterns).
- [ ] `make up` redeploy succeeds and endpoint is smoke-tested.

---

## Pass 5 — Wire up report delete in the UI

### Goal

Let users delete individual reports from the reports list page.

### Required work

1. In `src/lib/api.ts`, add inside the `reports` namespace:
   ```ts
   delete: (reportId: string) => apiClient.delete<void>(`/reports/${reportId}`).then(() => true),
   ```

2. In `src/pages/ReportsPage.tsx`:
   a. Add `deleteConfirmId` state (`string | null`, initialised to `null`).
   b. Add a `deleteMutation` that calls `api.reports.delete(id)`, invalidates the reports
      query for the current workspace on success, and resets `deleteConfirmId`.
   c. Add a delete button to each report card/row. Place it consistently with how the delete
      button appears on workspace cards (Pass 1) — corner or footer action row.
   d. Add the confirmation modal. Copy:
      *"This will permanently delete this report and all its messages. This action cannot be undone."*
   e. If the user is currently viewing the report thread page for the report being deleted,
      navigate back to the reports list on success (use the router's `navigate` hook).

3. Optionally, if a report detail/thread view exists as a separate page
   (`/workspaces/:id/reports/:threadId`), also add a delete button there that navigates back
   to the reports list after deletion.

### Files to modify

- `src/lib/api.ts`
- `src/pages/ReportsPage.tsx`
- Optionally the report thread page if one exists

### Acceptance criteria

- [ ] Each report card/row has a delete button.
- [ ] Clicking opens the confirmation modal with the required copy.
- [ ] Cancel closes modal with no change.
- [ ] Confirm calls `DELETE /reports/{id}`, shows spinner, removes the card on success.
- [ ] If viewing the deleted report's thread page, the user is navigated back to the reports list.
- [ ] `make ci` passes.
- [ ] `make up` redeploy succeeds and the behaviour is verified in the browser.

---

## Pass 6 — Redeploy and full end-to-end verification

### Goal

Confirm the complete feature set works correctly in the deployed environment after all
prior passes are merged.

### Required work

1. Run `make up` to rebuild and redeploy all containers.

2. **API smoke tests** (curl or Python):
   - Authenticate and obtain a session cookie.
   - Create a scratch workspace, run a pipeline to produce content + a report.
   - `DELETE /workspaces/{id}` → 204; confirm workspace no longer appears in `GET /workspaces`.
   - Create a second scratch workspace with content.
   - `DELETE /content/{item_id}` → 204; confirm item gone from `GET /workspaces/{id}/content`.
   - `DELETE /reports/{report_id}` → 204; confirm report gone from `GET /workspaces/{id}/reports`.
   - Repeat each delete with a non-existent id → confirm 404.
   - Repeat each delete without auth → confirm 401.

3. **Web UI walkthrough** (manual, in browser):
   - Open the workspaces list. Delete a workspace via the UI. Confirm it disappears.
   - Open a workspace content page. Delete a content item. Confirm the row disappears.
     If a detail sheet was open, confirm it closed.
   - Open a workspace reports page. Delete a report. Confirm the card disappears.
   - Open a report thread page. Delete the report. Confirm navigation back to reports list.
   - For each deletion: confirm the confirmation modal appears, Cancel works, spinner appears
     during the request, and the item is gone on success.

4. Run the full QA test script and confirm it still passes:
   ```bash
   SME_BASE_URL=http://172.19.0.1:8000/api python3 tests/manual/opencode_full_flow_metalearth_real_feeds.py
   ```

### Acceptance criteria (overall)

- [ ] All pass-level criteria from Passes 1–5 are satisfied.
- [ ] `make ci` passes on the final commit.
- [ ] `make up` produces a healthy stack (all containers show healthy/running in `docker compose ps`).
- [ ] API smoke tests all pass as described above.
- [ ] Web UI walkthrough completes without errors or visual regressions.
- [ ] The full QA test script reports `Manual full-flow OpenCode QA PASSED`.
- [ ] No unrelated pages or features are broken (feeds, runs, settings, profile still work).

---

## Overall acceptance criteria

The feature is complete when **all** of the following are true:

1. Users can delete a workspace from the workspaces list page via a confirmation dialog.
2. Users can delete a content item from the content page via a confirmation dialog.
3. Users can delete a report from the reports page (and optionally from the report thread page) via a confirmation dialog.
4. All three delete actions call the correct API endpoints and receive `204` on success.
5. The UI removes the deleted item immediately without a full page reload.
6. All confirmation dialogs follow the established `FeedsPage` modal pattern.
7. `make ci` passes.
8. `make up` redeploy is clean.
9. The full QA script passes.

---

## Files expected to change

| File | Pass | Change |
|------|------|--------|
| `src/lib/api.ts` | 1, 3, 5 | Add/verify archive, content.delete, reports.delete |
| `src/pages/WorkspacesPage.tsx` | 1 | Add delete button + confirmation modal |
| `backend/app/services/content.py` | 2 | Add `delete_content_item()` |
| `backend/app/api/content.py` | 2 | Add `DELETE /content/{id}` route |
| `src/pages/ContentPage.tsx` | 3 | Add delete button + confirmation modal |
| `backend/app/services/report.py` | 4 | Add `delete_report()` |
| `backend/app/api/reports.py` | 4 | Add `DELETE /reports/{id}` route |
| `src/pages/ReportsPage.tsx` | 5 | Add delete button + confirmation modal |
| Report thread page (if exists) | 5 | Optionally add delete + navigate-back |
| `backend/tests/` | 2, 4 | New test cases for delete endpoints |
