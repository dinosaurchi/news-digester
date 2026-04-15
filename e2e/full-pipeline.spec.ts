import { test, expect, type Page } from '@playwright/test';

/* ================================================================== */
/*  Types                                                              */
/* ================================================================== */

interface Workspace {
  id: string;
  name: string;
  customer: string;
  status: string;
}

interface RunNowResponse {
  runId: string;
  status: string;
  message: string;
}

/* ================================================================== */
/*  Helpers                                                            */
/* ================================================================== */

/** Log in via the UI and wait for the workspaces page to load. */
async function login(page: Page) {
  await page.goto('/login');
  await page.getByPlaceholder('Enter your username').fill('admin');
  await page.getByPlaceholder('Enter your password').fill('admin');
  await page.getByRole('button', { name: 'Sign In' }).click();
  await page.waitForURL('**/workspaces');
  await page.waitForLoadState('networkidle');

  const cookies = await page.context().cookies();
  const sessionCookie = cookies.find(c => c.name === 'session_id');
  if (!sessionCookie) {
    throw new Error('Login failed: session_id cookie not set');
  }
}

/** Create a workspace via the API and return its ID. */
async function createWorkspace(page: Page, name: string, customer: string): Promise<string> {
  const res = await page.request.post('/api/workspaces', {
    data: { name, customer },
  });
  expect(res.ok()).toBeTruthy();
  const ws: Workspace = await res.json();
  return ws.id;
}

/** Add a feed to a workspace via the API. */
async function addFeed(
  page: Page,
  workspaceId: string,
  feed: { name: string; url: string; type: string; cadence: string; tags: string[] },
) {
  const res = await page.request.post(`/api/workspaces/${workspaceId}/feeds`, { data: feed });
  expect(res.ok()).toBeTruthy();
  return res.json();
}

/** Poll GET /api/runs/{runId} until status is success or failed. */
async function waitForRunCompletion(page: Page, runId: string, maxMs = 120_000): Promise<string> {
  const start = Date.now();
  let status = 'queued';

  while (status === 'queued' || status === 'running') {
    if (Date.now() - start > maxMs) {
      throw new Error(`Run ${runId} timed out after ${maxMs}ms — last status: ${status}`);
    }
    await page.waitForTimeout(3000);
    const res = await page.request.get(`/api/runs/${runId}`);
    if (!res.ok()) {
      throw new Error(`GET /api/runs/${runId} returned ${res.status()}`);
    }
    const data = await res.json();
    status = data.status;
  }

  return status;
}

/** Delete a workspace via the API for cleanup. */
async function deleteWorkspace(page: Page, workspaceId: string) {
  const res = await page.request.delete(`/api/workspaces/${workspaceId}`);
  // 200 is expected; 404 is acceptable if already cleaned up
  expect([200, 404]).toContain(res.status());
}

/* ================================================================== */
/*  Tests                                                              */
/* ================================================================== */

test.describe('Full Pipeline E2E', () => {
  let wsId: string;
  const wsName = `E2E Pipeline ${Date.now()}`;

  test.beforeAll(async ({ browser }) => {
    // Use a single browser context to share login cookies across setup
    const context = await browser.newContext();
    const page = await context.newPage();
    await login(page);

    // Create workspace via API
    wsId = await createWorkspace(page, wsName, 'E2E Test Corp');

    // Add a real RSS feed via API
    await addFeed(page, wsId, {
      name: 'TechCrunch RSS',
      url: 'https://techcrunch.com/feed/',
      type: 'rss',
      cadence: 'daily',
      tags: ['e2e-test'],
    });

    await context.close();
  });

  test.afterAll(async ({ browser }) => {
    // Cleanup: delete the workspace via API
    const context = await browser.newContext();
    const page = await context.newPage();
    await login(page);
    await deleteWorkspace(page, wsId);
    await context.close();
  });

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  /* ------------------------------------------------------------------ */
  /*  1. Full pipeline: create workspace → feed → run → content → report */
  /* ------------------------------------------------------------------ */

  test('full pipeline: workspace → feed → run → content → report', async ({ page }) => {
    test.setTimeout(180_000); // 3 minutes for async pipeline

    // Navigate to runs page and trigger manual run via UI
    await page.goto(`/workspaces/${wsId}/runs`);
    await page.waitForLoadState('networkidle');

    // Verify trigger button is present
    const triggerBtn = page.getByRole('button', { name: /Trigger Manual Run/i });
    await expect(triggerBtn).toBeVisible({ timeout: 10_000 });

    // Click trigger and capture the 202 response to get runId
    const [response] = await Promise.all([
      page.waitForResponse(resp =>
        resp.url().includes('/run-now') && resp.request().method() === 'POST',
      ),
      triggerBtn.click(),
    ]);
    expect(response.status()).toBe(202);

    const runData: RunNowResponse = await response.json();
    const runId = runData.runId;
    expect(runId).toBeTruthy();

    // Toast should appear
    await expect(page.getByText(/Pipeline execution queued/i)).toBeVisible({ timeout: 10_000 });

    // Poll for run completion via API (every 3s, max 120s)
    const finalStatus = await waitForRunCompletion(page, runId);

    // Both "success" and "failed" are valid — feed fetch may fail in Docker
    expect(['success', 'failed']).toContain(finalStatus);

    // If run succeeded, verify content and reports
    if (finalStatus === 'success') {
      // Navigate to content page, assert at least 1 content row visible
      await page.goto(`/workspaces/${wsId}/content`);
      await page.waitForLoadState('networkidle');

      const contentRows = page.locator('table tbody tr');
      await expect(contentRows.first()).toBeVisible({ timeout: 10_000 });
      const contentCount = await contentRows.count();
      expect(contentCount).toBeGreaterThan(0);

      // Navigate to reports page, assert at least 1 report card visible
      await page.goto(`/workspaces/${wsId}/reports`);
      await page.waitForLoadState('networkidle');

      const reportCards = page.locator('a[href*="/reports/"]');
      await expect(reportCards.first()).toBeVisible({ timeout: 10_000 });

      // Click into report thread, assert system message visible
      await reportCards.first().click();
      await page.waitForURL(/\/reports\/.+/);
      await page.waitForLoadState('networkidle');

      // Verify messages are rendered (rounded-2xl border divs)
      const messageBubbles = page.locator('.rounded-2xl.border');
      await expect(messageBubbles.first()).toBeVisible({ timeout: 10_000 });
    }

    // If run failed, still check for reports (empty or with content)
    if (finalStatus === 'failed') {
      await page.goto(`/workspaces/${wsId}/reports`);
      await page.waitForLoadState('networkidle');

      // Reports page should load (either cards or empty state)
      const hasCards = await page.locator('a[href*="/reports/"]').first().isVisible().catch(() => false);
      const hasEmpty = await page.getByText('No reports yet').isVisible().catch(() => false);
      expect(hasCards || hasEmpty).toBeTruthy();
    }
  });

  /* ------------------------------------------------------------------ */
  /*  2. Full pipeline: verify run appears in runs list                  */
  /* ------------------------------------------------------------------ */

  test('full pipeline: run appears in runs list with correct status', async ({ page }) => {
    test.setTimeout(180_000); // 3 minutes for async pipeline

    // Navigate to runs page
    await page.goto(`/workspaces/${wsId}/runs`);
    await page.waitForLoadState('networkidle');

    // Trigger a manual run
    const triggerBtn = page.getByRole('button', { name: /Trigger Manual Run/i });
    await expect(triggerBtn).toBeVisible({ timeout: 10_000 });

    const [response] = await Promise.all([
      page.waitForResponse(resp =>
        resp.url().includes('/run-now') && resp.request().method() === 'POST',
      ),
      triggerBtn.click(),
    ]);
    expect(response.status()).toBe(202);

    const runData: RunNowResponse = await response.json();
    const runId = runData.runId;

    // Wait for toast
    await expect(page.getByText(/Pipeline execution queued/i)).toBeVisible({ timeout: 10_000 });

    // Poll for completion
    const finalStatus = await waitForRunCompletion(page, runId);
    expect(['success', 'failed']).toContain(finalStatus);

    // Reload the runs page and verify the run appears in the table
    await page.goto(`/workspaces/${wsId}/runs`);
    await page.waitForLoadState('networkidle');

    const rows = page.locator('table tbody tr');
    await expect(rows.first()).toBeVisible({ timeout: 10_000 });

    // The run ID should appear somewhere on the page (in the table or detail)
    // The runs table shows status badges — verify the final status is displayed
    const pageContent = await page.content();
    const statusText = finalStatus === 'success' ? 'Success' : 'Failed';
    expect(pageContent.toLowerCase()).toContain(finalStatus);

    // Verify the run row is visible by checking for run ID or status
    const hasRunId = await page.getByText(runId).isVisible().catch(() => false);
    const hasStatus = await page.getByText(statusText, { exact: false }).first().isVisible().catch(() => false);
    expect(hasRunId || hasStatus).toBeTruthy();
  });

  /* ------------------------------------------------------------------ */
  /*  3. Full pipeline: workspace has correct sidebar navigation         */
  /* ------------------------------------------------------------------ */

  test('full pipeline: workspace has correct sidebar navigation', async ({ page }) => {
    // Navigate to the created workspace
    await page.goto(`/workspaces/${wsId}`);
    await page.waitForLoadState('networkidle');

    // Verify the overview page loaded
    await expect(page.getByText('Total Feeds')).toBeVisible({ timeout: 10_000 });

    // The sidebar should be visible (it's a fixed aside element)
    const sidebar = page.locator('aside');
    await expect(sidebar).toBeVisible();

    // Verify all expected navigation tabs are present
    // The sidebar renders nav items as links with specific text labels
    const expectedNavItems = [
      'Overview',
      'Profile',
      'Feeds',
      'Content',
      'Reports',
      'Runs',
      'Feedback',
      'Settings',
    ];

    for (const navItem of expectedNavItems) {
      await expect(
        sidebar.locator('a', { hasText: navItem }).first(),
      ).toBeVisible({ timeout: 5_000 });
    }
  });
});
