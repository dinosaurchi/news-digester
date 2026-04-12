import { test, expect, type Page, type APIRequestContext } from '@playwright/test';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Workspace {
  id: string;
  name: string;
  customer: string;
  status: string;
}

interface ReportThread {
  id: string;
  workspaceId: string;
  title: string;
  status: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

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
async function createWorkspace(
  request: APIRequestContext,
  name: string,
  customer: string,
): Promise<string> {
  const res = await request.post('/api/workspaces', {
    data: { name, customer },
  });
  expect(res.ok()).toBeTruthy();
  const ws: Workspace = await res.json();
  return ws.id;
}

/** Fetch the list of reports for a workspace via the API. */
async function getReports(
  request: APIRequestContext,
  workspaceId: string,
): Promise<ReportThread[]> {
  const res = await request.get(`/api/workspaces/${workspaceId}/reports`);
  expect(res.ok()).toBeTruthy();
  return res.json();
}

/* ------------------------------------------------------------------ */
/*  Shared selectors                                                   */
/* ------------------------------------------------------------------ */

/** Locate the confirmation modal dialog container. */
function getModalDialog(page: Page) {
  return page.locator('.fixed.inset-0.z-50').last();
}

/** Locate the Cancel button inside the visible modal. */
function getModalCancelButton(page: Page) {
  return getModalDialog(page).getByRole('button', { name: 'Cancel' });
}

/** Locate the red Delete button inside the visible modal. */
function getModalDeleteButton(page: Page) {
  return getModalDialog(page).getByRole('button', { name: 'Delete' });
}

/** Locate the Loader2 spinner icon inside the modal's Delete button (pending state). */
function getModalDeleteSpinner(page: Page) {
  return getModalDeleteButton(page).locator('svg.animate-spin');
}

/* ------------------------------------------------------------------ */
/*  Tests                                                              */
/* ------------------------------------------------------------------ */

test.describe('Delete UI', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  /* ---------- Workspace delete ---------- */

  test('delete workspace from list', async ({ page, request }) => {
    // 1. Create a new workspace via API so we can safely delete it
    const wsName = `E2E Delete Test ${Date.now()}`;
    const _wsId = await createWorkspace(request, wsName, 'E2E Customer');

    // 2. Navigate to workspaces list
    await page.goto('/workspaces');
    await page.waitForLoadState('networkidle');

    // 3. Verify the new workspace card is visible
    await expect(page.getByText(wsName)).toBeVisible();

    // 4. Click the trash icon on the new workspace card
    const wsCard = page.locator('a[href*="/workspaces/"]').filter({ hasText: wsName });
    await wsCard.locator('button[title="Archive workspace"]').click();

    // 5. Verify confirmation modal appears with correct heading and warning text
    const modal = getModalDialog(page);
    await expect(modal).toBeVisible();
    await expect(modal.getByText('Archive Workspace')).toBeVisible();
    await expect(
      modal.getByText(
        'This will permanently archive the workspace and all its data. This action cannot be undone.',
      ),
    ).toBeVisible();

    // 6. Click the Delete button in the modal and wait for the archive API call
    const [response] = await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/api/workspaces/') && resp.request().method() === 'DELETE'),
      getModalDeleteButton(page).click(),
    ]);
    expect(response.status()).toBe(200);

    // 7. Wait for modal to close (indicates mutation completed), then verify
    //    the workspace card disappears from the list
    await expect(modal).not.toBeVisible({ timeout: 10000 });
    await expect(page.getByText(wsName)).not.toBeVisible({ timeout: 10000 });
  });

  test('cancel workspace delete does nothing', async ({ page }) => {
    // 1. Navigate to workspaces
    await page.goto('/workspaces');
    await page.waitForLoadState('networkidle');

    // 2. Find the first workspace card name (pick a seed workspace)
    const firstCard = page.locator('a[href*="/workspaces/"]').first();
    const wsName = await firstCard.locator('h3').textContent();

    // 3. Click trash icon on that workspace
    await firstCard.locator('button[title="Archive workspace"]').click();

    // 4. Verify modal appears
    const modal = getModalDialog(page);
    await expect(modal).toBeVisible();
    await expect(modal.getByText('Archive Workspace')).toBeVisible();

    // 5. Click Cancel
    await getModalCancelButton(page).click();

    // 6. Verify modal closes and workspace is still in the list
    await expect(modal).not.toBeVisible();
    await expect(page.getByText(wsName!)).toBeVisible();
  });

  /* ---------- Content delete ---------- */

  test('delete content item from content page', async ({ page }) => {
    // 1. Navigate to content page for ws-1
    await page.goto('/workspaces/ws-1/content');
    await page.waitForLoadState('networkidle');

    // 2. Wait for content rows to load
    const rows = page.locator('table tbody tr');
    await expect(rows.first()).toBeVisible();

    // 3. Capture the title of the first content row before deleting
    const firstRowTitle = await rows.first().locator('td').first().textContent();

    // 4. Click trash icon on the first content row
    await rows.first().locator('button[title="Delete content item"]').click();

    // 5. Verify confirmation modal appears
    const modal = getModalDialog(page);
    await expect(modal).toBeVisible();
    await expect(modal.getByText('Delete Content Item')).toBeVisible();
    await expect(
      modal.getByText(
        'This will permanently delete this content item. This action cannot be undone.',
      ),
    ).toBeVisible();

    // 6. Click Delete and wait for the delete API call
    const [response] = await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/api/content/') && resp.request().method() === 'DELETE'),
      getModalDeleteButton(page).click(),
    ]);
    expect(response.status()).toBe(204);

    // 7. Wait for modal to close, then verify the deleted item's title is no longer in the table.
    //    The content table uses client-side pagination (PAGE_SIZE=10), so deleting one item
    //    from a page with more than 10 total items will cause the next item to fill the gap,
    //    keeping the row count the same. Instead, assert the specific item is gone.
    await expect(modal).not.toBeVisible({ timeout: 10000 });
    await expect(page.getByText(firstRowTitle!)).not.toBeVisible({ timeout: 10000 });
  });

  test('delete content item closes detail sheet if open', async ({ page }) => {
    // 1. Navigate to content page for ws-1
    await page.goto('/workspaces/ws-1/content');
    await page.waitForLoadState('networkidle');

    // 2. Wait for content rows to load
    const rows = page.locator('table tbody tr');
    await expect(rows.first()).toBeVisible();

    // 3. Click on a content row to open the detail sheet
    await rows.first().click();

    // 4. Verify detail sheet is visible (the Sheet renders a fixed panel)
    const sheetPanel = page.locator('.fixed.inset-0.z-50.flex.justify-end');
    await expect(sheetPanel).toBeVisible();

    // 5. Click the trash icon for the same content item. Use dispatchEvent
    //    because the sheet backdrop covers the table — a normal or
    //    force-click would be intercepted by the backdrop. dispatchEvent
    //    fires the click directly on the button DOM element, bypassing
    //    the browser's hit-testing, so the button's stopPropagation and
    //    setDeleteConfirmId run correctly.
    await rows.first().locator('button[title="Delete content item"]').dispatchEvent('click');

    // 6. Verify the delete confirmation modal appears on top of the sheet
    const modal = getModalDialog(page);
    await expect(modal).toBeVisible();
    await expect(modal.getByText('Delete Content Item')).toBeVisible();

    // 7. Click Delete in modal — the mutation onSuccess checks
    //    `if (deleteConfirmId === selectedId)` and closes the sheet
    await getModalDeleteButton(page).click();

    // 8. Wait for modal to close, then verify both modal and sheet are closed
    await expect(modal).not.toBeVisible({ timeout: 10000 });
    await expect(sheetPanel).not.toBeVisible({ timeout: 10000 });
  });

  /* ---------- Report delete ---------- */

  test('delete report from reports list', async ({ page }) => {
    // 1. Navigate to reports page for ws-1
    await page.goto('/workspaces/ws-1/reports');
    await page.waitForLoadState('networkidle');

    // 2. Wait for report cards to load
    const reportCards = page.locator('a[href*="/workspaces/ws-1/reports/"]');
    const initialCount = await reportCards.count();
    expect(initialCount).toBeGreaterThan(0);

    // 3. Click trash icon on the first report card
    await reportCards.first().locator('button[title="Delete report"]').click();

    // 4. Verify confirmation modal appears
    const modal = getModalDialog(page);
    await expect(modal).toBeVisible();
    await expect(modal.getByText('Delete Report')).toBeVisible();
    await expect(
      modal.getByText(
        'This will permanently delete this report and all its messages. This action cannot be undone.',
      ),
    ).toBeVisible();

    // 5. Click Delete
    await getModalDeleteButton(page).click();

    // 6. Verify modal closes and report card count decreased by 1
    await expect(modal).not.toBeVisible();
    await expect(reportCards).toHaveCount(initialCount - 1);
  });

  test('delete report from thread page navigates back', async ({ page, request }) => {
    // 1. Get a report's thread ID from the API
    const reports = await getReports(request, 'ws-1');
    expect(reports.length).toBeGreaterThan(0);
    const threadId = reports[0].id;

    // 2. Navigate to the report thread page
    await page.goto(`/workspaces/ws-1/reports/${threadId}`);
    await page.waitForLoadState('networkidle');

    // 3. Verify thread page loaded — use h2.truncate because the thread
    //    title is the only h2 with the truncate class (markdown h2 headings
    //    rendered inside messages don't have it).
    await expect(page.locator('h2.truncate')).toBeVisible();

    // 4. Click the delete button in the thread header
    await page.locator('button[title="Delete report"]').click();

    // 5. Verify confirmation modal appears
    const modal = getModalDialog(page);
    await expect(modal).toBeVisible();
    await expect(modal.getByText('Delete Report')).toBeVisible();

    // 6. Click Delete
    await getModalDeleteButton(page).click();

    // 7. Verify navigation back to reports list
    await page.waitForURL('**/workspaces/ws-1/reports');
    await expect(page.getByText('Intelligence Reports')).toBeVisible();
  });

  /* ---------- Spinner / pending state ---------- */

  test('confirmation modal shows spinner during pending mutation', async ({ page, request }) => {
    // 1. Create a workspace to delete
    const wsName = `E2E Spinner Test ${Date.now()}`;
    await createWorkspace(request, wsName, 'E2E Customer');

    await page.goto('/workspaces');
    await page.waitForLoadState('networkidle');

    // 2. Open the delete confirmation modal for the new workspace
    const wsCard = page.locator('a[href*="/workspaces/"]').filter({ hasText: wsName });
    await wsCard.locator('button[title="Archive workspace"]').click();

    const modal = getModalDialog(page);
    await expect(modal).toBeVisible();

    // 3. Intercept the archive API call and delay the response to keep
    //    the mutation in a pending state so the spinner is visible.
    await page.route('**/api/workspaces/**', async (route) => {
      await new Promise((r) => setTimeout(r, 1500));
      await route.continue();
    });

    // 4. Click Delete — the spinner should appear on the button
    const deleteButton = getModalDeleteButton(page);
    await deleteButton.click();

    // 5. Verify the spinner icon (animate-spin) appears inside the Delete button
    await expect(getModalDeleteSpinner(page)).toBeVisible();

    // 6. After the delayed response, the modal should close
    await expect(modal).not.toBeVisible({ timeout: 10_000 });
  });
});
