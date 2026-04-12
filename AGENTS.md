## Rules

- Fail fast, do not hide errors, do not walk around to skip or bypass any steps or tests.
- If being asked to commit changes, commit with `git commit -m "<message>"`.
  - Commit with the current Author (check previous commits to see the author).
  - To specify that the commit is from AI, add `[AI]` prefix to the commit message.
- All data is stored in the `data/` directory. DO NOT commit any data to the repository.
- All temporary-ephemeral files are stored in the `.ai/tmp/` directory.
- For Opencode agent, do not try to parallelize the work, just do one task at a time sequentially.
- Before finishing works, make sure the command `make ci` passes.

---

## E2E Testing with Playwright

### Overview

This project uses **Playwright** (`@playwright/test`) for browser-based end-to-end tests. Tests live in `e2e/` and are separate from the Vitest unit tests in `src/__tests__/`.

### Critical: Docker-in-Docker networking

**This environment is itself a Docker container.** You cannot use `localhost:3000` to reach the app — that resolves to the agent container, not the host. The app runs in a sibling Docker container.

To reach app services from this environment, use the **Docker bridge gateway IP**:

```bash
# Find the bridge gateway (usually 172.17.0.1)
docker network inspect bridge --format '{{range .IPAM.Config}}{{.Gateway}}{{end}}'

# Or find a specific service's IP
docker inspect sme-news-admin --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'

# Verify the app is reachable
curl -s -o /dev/null -w "%{http_code}" http://172.17.0.1:3000
```

The Playwright config uses `baseURL: 'http://172.17.0.1:3000'`. If this IP ever changes, update `playwright.config.ts` accordingly.

### Running tests

```bash
# Install Playwright browsers (first time only)
npx playwright install --with-deps chromium

# Run all E2E tests
npx playwright test --reporter=list

# Run a single test
npx playwright test --reporter=line "delete workspace from list"

# Run with UI (if supported)
npx playwright test --ui

# Run with debug mode
npx playwright test --debug
```

### Redeploying before tests

After code changes, the Docker containers must be rebuilt to pick up new code:

```bash
make down && make up
```

Then verify services are healthy:
```bash
docker compose ps                    # all should be Up/healthy
docker exec sme-news-admin-backend curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/workspaces
docker exec sme-news-admin curl -s -o /dev/null -w "%{http_code}" http://localhost:80
```

### Authentication

The app uses cookie-based session auth. Login programmatically in tests:

```typescript
async function login(page: Page) {
  await page.goto('/login');
  await page.getByPlaceholder('Enter your username').fill('admin');
  await page.getByPlaceholder('Enter your password').fill('admin');
  await page.getByRole('button', { name: 'Sign In' }).click();
  await page.waitForURL('**/workspaces');
  await page.waitForLoadState('networkidle');
  // Verify cookie is set
  const cookies = await page.context().cookies();
  if (!cookies.find(c => c.name === 'session_id')) {
    throw new Error('Login failed: session_id cookie not set');
  }
}
```

Default credentials: `admin` / `admin` (from `backend/app/config.py`).

**Important:** Sessions are in-memory. After `make down && make up`, all sessions are lost and login must happen again.

### Creating test data via API

Workspaces can be created directly via API (no auth required):

```typescript
async function createWorkspace(page: Page, name: string): Promise<string> {
  const resp = await page.request.post('/api/workspaces', {
    data: { name, customer: 'E2E Test' },
  });
  const body = await resp.json();
  return body.id;
}
```

**Content items and reports cannot be created via API** — they are produced only by the pipeline (which requires the OpenCode agent). Use the **seed data** instead:
- Workspace `ws-1` ("TechCorp Strategy") has 12 content items and 3 reports with messages
- The seed runs automatically on first startup if the database is empty
- Seed is idempotent (skips if data exists)

To check available seed data:
```bash
curl http://172.17.0.1:8000/api/workspaces/ws-1/content | python3 -m json.tool | head -50
curl http://172.17.0.1:8000/api/workspaces/ws-1/reports | python3 -m json.tool | head -50
```

### UI routes

| Route | Page |
|---|---|
| `/login` | Login page |
| `/workspaces` | Workspace list |
| `/workspaces/:workspaceId` | Workspace overview |
| `/workspaces/:workspaceId/content` | Content items (table with client-side pagination, `PAGE_SIZE = 10`) |
| `/workspaces/:workspaceId/reports` | Reports list |
| `/workspaces/:workspaceId/reports/:threadId` | Report thread detail |
| `/workspaces/:workspaceId/feeds` | Feeds |
| `/workspaces/:workspaceId/settings` | Settings (has archive workspace button) |

### Key gotchas from experience

1. **Client-side pagination**: ContentPage uses `PAGE_SIZE = 10` client-side. Deleting an item from a full page won't reduce row count — the next item fills the gap. Assert on the specific item's absence, not on row count.

2. **Workspace delete returns 200, not 204**: `DELETE /workspaces/{id}` is a soft-delete that returns the archived workspace object (HTTP 200). Content and report deletes return 204.

3. **Sheet backdrop blocks clicks**: When a detail sheet (drawer) is open, its backdrop overlay intercepts clicks on table row buttons. Use `dispatchEvent('click')` to bypass browser hit-testing, or close the sheet first.

4. **`credentials: 'include'`**: The API client (`src/lib/api-client.ts`) must send cookies with requests. Verify `credentials: 'include'` is set in the `fetch` call.

5. **Query invalidation keys must match**: When using React Query's `invalidateQueries`, the prefix must match the `useQuery` key exactly. If the query key includes a filters object (e.g., `['content', workspaceId, filters]`), use the broadest prefix `['content']` to avoid object-reference mismatch issues.

6. **Backend filtering assumptions**: Don't assume the handoff plan is correct about backend behavior. Verify: e.g., `GET /workspaces` was documented as "already filters by active" but actually returned all workspaces including archived. Always verify with curl.

7. **`h2` elements are not unique**: Report thread pages render markdown that can contain `## headings`, so `locator('h2')` may match multiple elements. Use more specific selectors like `h2.truncate`.

### API testing (without Playwright)

For backend API smoke tests, use `curl` directly — no browser needed:

```bash
# Login and save cookie
curl -s -c /tmp/cookies.txt -X POST http://172.17.0.1:8000/api/session/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}'

# Use cookie for authenticated endpoints
curl -s -b /tmp/cookies.txt -X DELETE http://172.17.0.1:8000/api/content/ci-1 -w "\n%{http_code}\n"
curl -s -b /tmp/cookies.txt -X DELETE http://172.17.0.1:8000/api/reports/report-1 -w "\n%{http_code}\n"

# Unauthenticated should return 401
curl -s -X DELETE http://172.17.0.1:8000/api/content/ci-1 -w "\n%{http_code}\n"

# Non-existent should return 404
curl -s -b /tmp/cookies.txt -X DELETE http://172.17.0.1:8000/api/content/nonexistent -w "\n%{http_code}\n"
```

### Writing new E2E tests

1. Add test files in `e2e/` with `.spec.ts` extension
2. Use the `login()` helper from existing tests (or import/share it)
3. Prefer API calls (`page.request.post()`) over UI interactions for test data setup
4. Use `page.waitForResponse()` to assert on API response codes
5. Use `expect(locator).not.toBeVisible({ timeout: 10000 })` for mutations that update the DOM
6. Run `make ci` before committing — Playwright tests are NOT part of CI (CI only runs Vitest and pytest)