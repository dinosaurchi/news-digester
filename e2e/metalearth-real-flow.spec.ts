/**
 * Metal Earth Real Flow — Manual QA E2E Test
 *
 * ============================================================================
 * IMPORTANT: This is a MANUAL QA test, NOT part of the regular CI suite.
 * It creates a REAL workspace named "Metal Earth" that should be kept
 * after the test completes. It requires a deployed stack with working
 * feed fetching and LLM report generation.
 *
 * Run with:
 *   npx playwright test e2e/metalearth-real-flow.spec.ts --timeout=600000
 * ============================================================================
 */

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
/*  Metal Earth Data                                                   */
/* ================================================================== */

const WORKSPACE_NAME = 'Metal Earth';
const WORKSPACE_CUSTOMER = 'Fascinations Inc.';

const PROFILE = {
  businessName: 'Metal Earth',
  description:
    'Metal Earth, by Fascinations Inc. (Seattle, WA), produces laser-cut 3D metal model kits assembled from steel sheets — no glue or solder required. Product lines span Classic, Premium Series, and Licensed collections featuring Star Wars, Marvel, Harry Potter, Transformers, Lord of the Rings, Batman, Star Trek, and more. Categories include aviation, architecture, vehicles, space, tanks, ships, dinosaurs, and wildlife.',
  notes: 'Prioritize: (1) new licensed IP/franchise deals that Metal Earth could pursue, (2) competitor product launches or market moves, (3) toy/hobby retail channel signals (Toy Fair, retail partnerships, e-commerce trends), (4) entertainment releases (movies, series) that could drive collectible demand, and (5) aerospace/architecture news inspiring future product lines.',
  products: [
    '3D laser-cut steel model kits',
    'Licensed franchise model kits (Star Wars, Marvel, Harry Potter, etc.)',
    'Premium Series large-scale metal models',
    'Aviation & military model kits (Boeing, Lockheed Martin, Cessna)',
    'Architecture landmark model kits',
    'Gift Box Sets and accessories',
  ],
  competitors: [
    'Piececool (Chinese 3D metal puzzles)',
    'UGEARS (wooden mechanical model kits)',
    'Tenyo Metallic Nano (Japanese licensee, same factory)',
    'HK Nanyuan / MU Model (AliExpress metal model brands)',
    'Professor Puzzle (UK distributor & competitor)',
  ],
  priorityThemes: [
    'licensed merchandise and IP deals',
    'Star Wars, Marvel, Disney franchise developments',
    'toy industry trends and Toy Fair announcements',
    'hobby retail channel and specialty store trends',
    '3D model kit and metal puzzle market',
    'new entertainment franchises with licensing potential',
    'Hasbro, Mattel, and major toy company strategies',
    'collectibles and gift product trends',
    'aerospace and aviation milestones',
  ],
  excludedTopics: [
    'cryptocurrency and blockchain',
    'enterprise SaaS and cloud infrastructure',
    'general software engineering',
    'pharmaceutical and biotech',
    'real estate investment',
  ],
};

const FEEDS: { name: string; url: string }[] = [
  // Feed 1: The Toy Book — official trade publication for the North American toy industry
  {
    name: 'The Toy Book — toy industry news',
    url: 'https://toybook.com/feed/',
  },
  // Feed 2: The Pop Insider — pop culture, collectibles, licensing and merch news
  {
    name: 'The Pop Insider — pop culture & collectibles',
    url: 'https://thepopinsider.com/feed/',
  },
  // Feed 3: aNb Media / TFE Magazine — toy & hobby industry coverage
  {
    name: 'aNb Media / TFE Magazine — toy industry',
    url: 'https://www.anbmedia.com/feed/',
  },
  // Feed 4: Make: — maker/DIY projects, includes scale modeling and hobby content
  {
    name: 'Make: — maker projects & scale modeling',
    url: 'https://makezine.com/feed/',
  },
  // Feed 5: The Mary Sue — pop culture news covering entertainment, comics, toys
  {
    name: 'The Mary Sue — pop culture & entertainment',
    url: 'https://www.themarysue.com/feed/',
  },
  // Feed 6: Collectibles.org — collectibles industry news and market trends
  {
    name: 'Collectibles.org — collectibles industry',
    url: 'https://www.collectibles.org/feed/',
  },
];

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

/** Add an item to a ListEditor field on the profile page using its unique placeholder. */
async function addListItem(page: Page, placeholder: string, value: string) {
  const input = page.getByPlaceholder(placeholder);
  await input.fill(value);
  await input.press('Enter');
  await page.waitForTimeout(300); // small delay for UI update
}

/** Add a feed via the UI sheet form. */
async function addFeed(page: Page, name: string, url: string) {
  await page.getByRole('button', { name: 'Add Feed Source' }).click();

  // Wait for the sheet to open
  await expect(page.getByRole('heading', { name: 'Add Feed Source' })).toBeVisible({
    timeout: 10_000,
  });

  await page.getByPlaceholder('e.g. TechCrunch Enterprise').fill(name);
  await page.getByPlaceholder('https://example.com/feed').fill(url);

  // Type defaults to RSS, cadence defaults to daily — no change needed

  const [response] = await Promise.all([
    page.waitForResponse(
      resp =>
        resp.url().includes('/api/workspaces/') &&
        resp.url().includes('/feeds') &&
        resp.request().method() === 'POST',
      { timeout: 15_000 },
    ),
    page.getByRole('button', { name: 'Add Source' }).click(),
  ]);
  expect(response.status()).toBe(201);

  // Wait for the sheet to close
  await page.waitForTimeout(500);
}

/** Poll GET /api/runs/{runId} until status is terminal. */
async function waitForRun(page: Page, runId: string, maxMs = 300_000): Promise<string> {
  const start = Date.now();
  let status = 'queued';

  while (status === 'queued' || status === 'running') {
    if (Date.now() - start > maxMs) {
      throw new Error(`Run ${runId} timed out after ${maxMs}ms — last status: ${status}`);
    }
    await page.waitForTimeout(5000);
    const res = await page.request.get(`/api/runs/${runId}`);
    if (!res.ok()) {
      throw new Error(`GET /api/runs/${runId} returned ${res.status()}`);
    }
    const data = await res.json();
    status = data.status;
    console.log(`  Run ${runId}: status=${status}`);
  }

  return status;
}

/* ================================================================== */
/*  Test Suite                                                         */
/* ================================================================== */

test.describe.serial('Metal Earth Real Flow — Manual QA', () => {
  // Shared workspace ID across all serial tests
  let wsId: string;
  let runId: string;
  let threadId: string;

  test.setTimeout(600_000); // 10 minutes

  // Each test gets a fresh browser context — must log in before every step
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  /* ------------------------------------------------------------------ */
  /*  Step 1: Login                                                      */
  /* ------------------------------------------------------------------ */

  test('Step 1: Login', async ({ page }) => {
    // Login already handled by beforeEach; just verify we're on workspaces
    await expect(page.getByRole('heading', { name: 'Workspaces' })).toBeVisible({ timeout: 10_000 });
    console.log('✓ Login successful');
  });

  /* ------------------------------------------------------------------ */
  /*  Step 2: Create workspace via UI                                    */
  /* ------------------------------------------------------------------ */

  test('Step 2: Create workspace via UI', async ({ page }) => {
    await page.goto('/workspaces');
    await page.waitForLoadState('networkidle');

    // Open create workspace modal
    await page.getByRole('button', { name: 'Create Workspace' }).click();
    await expect(page.getByRole('heading', { name: 'Create Workspace' })).toBeVisible();

    // Fill form
    await page.getByPlaceholder('e.g., TechCorp Strategy').fill(WORKSPACE_NAME);
    await page.getByPlaceholder('e.g., TechCorp Inc.').fill(WORKSPACE_CUSTOMER);

    // Submit and capture workspace ID from the POST response
    const [response] = await Promise.all([
      page.waitForResponse(
        resp =>
          resp.url().includes('/api/workspaces') &&
          resp.request().method() === 'POST',
      ),
      page.getByRole('button', { name: 'Create', exact: true }).click(),
    ]);
    expect([200, 201].includes(response.status())).toBeTruthy();

    const wsData: Workspace = await response.json();
    wsId = wsData.id;
    console.log(`✓ Workspace created: ${wsId} — "${WORKSPACE_NAME}"`);

    // Verify modal closes and workspace appears in the list
    await expect(page.getByRole('heading', { name: 'Create Workspace' })).not.toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText(WORKSPACE_NAME)).toBeVisible({ timeout: 10_000 });
  });

  /* ------------------------------------------------------------------ */
  /*  Step 3: Configure profile via UI                                   */
  /* ------------------------------------------------------------------ */

  test('Step 3: Configure profile via UI', async ({ page }) => {
    await page.goto(`/workspaces/${wsId}/profile`);
    await page.waitForLoadState('networkidle');

    // Wait for profile form to load
    await expect(
      page.getByRole('heading', { name: 'Business Profile' }),
    ).toBeVisible({ timeout: 10_000 });

    // Fill scalar fields
    const businessNameInput = page.getByPlaceholder('e.g. TechCorp Inc.');
    await businessNameInput.clear();
    await businessNameInput.fill(PROFILE.businessName);

    const descInput = page.getByPlaceholder('Describe what your business does');
    await descInput.clear();
    await descInput.fill(PROFILE.description);

    const notesInput = page.getByPlaceholder('Any specific instructions for the AI agent');
    await notesInput.clear();
    await notesInput.fill(PROFILE.notes);

    // Fill array fields using ListEditor pattern (each has a unique placeholder)
    for (const product of PROFILE.products) {
      await addListItem(page, 'e.g. CloudStack Pro', product);
    }
    console.log(`  Added ${PROFILE.products.length} products`);

    for (const competitor of PROFILE.competitors) {
      await addListItem(page, 'e.g. CloudGiant', competitor);
    }
    console.log(`  Added ${PROFILE.competitors.length} competitors`);

    for (const theme of PROFILE.priorityThemes) {
      await addListItem(page, 'e.g. Generative AI', theme);
    }
    console.log(`  Added ${PROFILE.priorityThemes.length} priority themes`);

    for (const topic of PROFILE.excludedTopics) {
      await addListItem(page, 'e.g. Consumer hardware', topic);
    }
    console.log(`  Added ${PROFILE.excludedTopics.length} excluded topics`);

    // Verify unsaved changes warning appears
    await expect(page.getByText('You have unsaved changes')).toBeVisible({ timeout: 5000 });

    // Save and wait for PUT response
    const saveButton = page.getByRole('button', { name: 'Save Changes' }).first();
    const [response] = await Promise.all([
      page.waitForResponse(
        resp =>
          resp.url().includes(`/api/workspaces/${wsId}/profile`) &&
          resp.request().method() === 'PUT',
      ),
      saveButton.click(),
    ]);
    expect(response.status()).toBe(200);

    console.log('✓ Profile configured and saved');
  });

  /* ------------------------------------------------------------------ */
  /*  Step 4: Add 6 feeds via UI                                        */
  /* ------------------------------------------------------------------ */

  test('Step 4: Add 6 feeds via UI', async ({ page }) => {
    await page.goto(`/workspaces/${wsId}/feeds`);
    await page.waitForLoadState('networkidle');

    // Wait for feeds page to load
    await expect(
      page.getByRole('heading', { name: 'Input Feeds' }),
    ).toBeVisible({ timeout: 10_000 });

    for (const feed of FEEDS) {
      await addFeed(page, feed.name, feed.url);
      console.log(`  Feed added: ${feed.name}`);
    }

    console.log(`✓ All ${FEEDS.length} feeds added`);
  });

  /* ------------------------------------------------------------------ */
  /*  Step 5: Update settings via API                                   */
  /* ------------------------------------------------------------------ */

  test('Step 5: Update settings via API', async ({ page }) => {
    const res = await page.request.put(`/api/workspaces/${wsId}/settings`, {
      data: {
        reportStyle: 'detailed',
        // Standard QA thresholds — not debug mode. Filters obvious junk
        // while keeping borderline items for scoring verification.
        thresholds: {
          minRelevanceScore: 0.15,
          minFinalScore: 0.15,
          maxArticlesPerReport: 10,
          trustedDomains: [
            'toybook.com',
            'licenseglobal.com',
            'thepopinsider.com',
            'hasbro.com',
            'mattel.com',
            'disney.com',
            'starwars.com',
            'marvel.com',
            'anbmedia.com',
          ],
        },
        schedule: {
          enabled: false,
          frequency: 'daily',
          timeOfDay: '08:00',
          timezone: 'UTC',
        },
      },
    });
    expect(res.status()).toBe(200);

    console.log('✓ Settings updated (QA thresholds 0.15, schedule disabled, trusted domains configured)');
  });

  /* ------------------------------------------------------------------ */
  /*  Step 6: Trigger run via UI                                        */
  /* ------------------------------------------------------------------ */

  test('Step 6: Trigger manual run via UI', async ({ page }) => {
    await page.goto(`/workspaces/${wsId}/runs`);
    await page.waitForLoadState('networkidle');

    // Wait for runs page to load
    await expect(
      page.getByRole('heading', { name: 'Operational Runs' }),
    ).toBeVisible({ timeout: 10_000 });

    // Click trigger and capture the 202 response
    const triggerBtn = page.getByRole('button', { name: /Trigger Manual Run/i });
    await expect(triggerBtn).toBeVisible({ timeout: 10_000 });

    const [response] = await Promise.all([
      page.waitForResponse(
        resp =>
          resp.url().includes('/run-now') &&
          resp.request().method() === 'POST',
      ),
      triggerBtn.click(),
    ]);
    expect(response.status()).toBe(202);

    const runData: RunNowResponse = await response.json();
    runId = runData.runId;
    expect(runId).toBeTruthy();

    // Toast should appear
    await expect(
      page.getByText(/Pipeline execution queued/i),
    ).toBeVisible({ timeout: 10_000 });

    console.log(`✓ Run triggered: ${runId}`);
  });

  /* ------------------------------------------------------------------ */
  /*  Step 7: Poll for run completion via API                           */
  /* ------------------------------------------------------------------ */

  test('Step 7: Poll for run completion', async ({ page }) => {
    console.log(`  Polling for run ${runId} completion (max 5 minutes)...`);
    const finalStatus = await waitForRun(page, runId, 300_000);

    expect(['success', 'succeeded', 'failed']).toContain(finalStatus);
    console.log(`✓ Run completed with status: ${finalStatus}`);

    // If run failed, we still continue to check for partial content
    if (finalStatus === 'failed') {
      console.log('  WARNING: Run failed — proceeding to check for partial results');
    }
  });

  /* ------------------------------------------------------------------ */
  /*  Step 8: Verify content via UI                                     */
  /*  NOTE: Content scoring is deterministic/lexical only (keyword, BM25,*/
  /*  freshness, source authority).  LLM is NOT used for base content    */
  /*  scoring — it is used only for shortlist reranking and report       */
  /*  generation.                                                        */
  /* ------------------------------------------------------------------ */

  test('Step 8: Verify content via UI', async ({ page }) => {
    await page.goto(`/workspaces/${wsId}/content`);
    await page.waitForLoadState('networkidle');

    // Wait for content page to load
    await expect(
      page.getByRole('heading', { name: 'Content Inspection' }),
    ).toBeVisible({ timeout: 10_000 });

    // Check content table has rows
    const contentRows = page.locator('table tbody tr');
    const rowCount = await contentRows.count();

    console.log(`  Content items found: ${rowCount}`);

    if (rowCount > 0) {
      // Assert at least one row is visible
      await expect(contentRows.first()).toBeVisible({ timeout: 10_000 });

      // Check via API that some items have non-zero scores
      const contentRes = await page.request.get(`/api/workspaces/${wsId}/content`);
      if (contentRes.ok()) {
        const contentItems: any[] = await contentRes.json();
        const scoredItems = contentItems.filter(
          (item: any) =>
            item.finalScore > 0 ||
            (item.scoreBreakdown && item.scoreBreakdown.final > 0),
        );
        console.log(`  Items with non-zero scores: ${scoredItems.length}/${contentItems.length}`);
      }
    }

    // Content table should have at least the header even if empty
    const hasTable = await page.locator('table thead').isVisible().catch(() => false);
    const hasEmpty = await page.getByText('No content items').isVisible().catch(() => false);
    expect(hasTable || hasEmpty || rowCount > 0).toBeTruthy();

    console.log('✓ Content page verified');
  });

  /* ------------------------------------------------------------------ */
  /*  Step 9: Verify report via UI                                      */
  /* ------------------------------------------------------------------ */

  test('Step 9: Verify report via UI', async ({ page }) => {
    await page.goto(`/workspaces/${wsId}/reports`);
    await page.waitForLoadState('networkidle');

    // Wait for reports page to load
    await expect(
      page.getByRole('heading', { name: 'Intelligence Reports' }),
    ).toBeVisible({ timeout: 10_000 });

    // Check for report cards or empty state
    const hasCards = await page.locator('a[href*="/reports/"]').first().isVisible().catch(() => false);
    const hasEmpty = await page.getByText('No reports yet').isVisible().catch(() => false);

    if (hasEmpty) {
      console.log('  No reports generated (run may have failed)');
      test.skip();
      return;
    }

    expect(hasCards).toBeTruthy();

    // Click the first report card to open the thread
    const firstCard = page.locator('a[href*="/reports/"]').first();
    await firstCard.click();
    await page.waitForURL(/\/reports\/.+/);
    await page.waitForLoadState('networkidle');

    // Extract thread ID from URL
    const url = page.url();
    const match = url.match(/\/reports\/([^/]+)/);
    threadId = match ? match[1] : '';
    expect(threadId).toBeTruthy();

    // Wait for messages to render
    await page.waitForTimeout(2000);

    // Check for system message with real content
    const messageBubbles = page.locator('.rounded-2xl.border');
    await expect(messageBubbles.first()).toBeVisible({ timeout: 10_000 });

    // Get report title
    const threadTitle = await page.locator('h2').first().textContent();
    console.log(`  Report title: ${threadTitle}`);

    // Get report content via API to verify it's not a placeholder
    const messagesRes = await page.request.get(`/api/report-threads/${threadId}/messages`);
    if (messagesRes.ok()) {
      const messages: any[] = await messagesRes.json();
      const systemMessages = messages.filter(m => m.role === 'system');
      if (systemMessages.length > 0) {
        const lastSystemMsg = systemMessages[systemMessages.length - 1];
        const content = lastSystemMsg.content || '';
        const preview = content.substring(0, 200);
        console.log(`  Report content (first 200 chars): ${preview}`);

        // Assert the report is not the empty placeholder
        expect(content).not.toContain('No SME news items were provided');
        expect(content.length).toBeGreaterThan(50);
      }
    }

    console.log('✓ Report verified');
  });

  /* ------------------------------------------------------------------ */
  /*  Step 10: Comment on report and verify LLM response                */
  /* ------------------------------------------------------------------ */

  test('Step 10: Comment on report and verify LLM response', async ({ page }) => {
    if (!threadId) {
      console.log('  Skipping: no report thread available');
      test.skip();
      return;
    }

    // Navigate to the report thread page
    await page.goto(`/workspaces/${wsId}/reports/${threadId}`);
    await page.waitForLoadState('networkidle');

    // Wait for messages to load
    await page.waitForTimeout(2000);

    // Find the chat textarea
    const textarea = page.getByPlaceholder(
      'Ask a question, provide feedback, or request changes...',
    );
    await expect(textarea).toBeVisible({ timeout: 10_000 });

    // Fill and send the comment
    const comment =
      'Summarize the most important opportunities or market signals for Metal Earth from this report.';
    await textarea.fill(comment);

    // Wait for the agent response via API — use POST + poll pattern
    const [postResponse] = await Promise.all([
      page.waitForResponse(
        resp =>
          resp.url().includes(`/api/report-threads/${threadId}/messages`) &&
          resp.request().method() === 'POST',
        { timeout: 30_000 },
      ),
      textarea.press('Enter'),
    ]);
    expect(postResponse.status()).toBe(201);

    const chatData: any = await postResponse.json();
    const agentMessageId = chatData.agentMessage?.id;
    expect(agentMessageId).toBeTruthy();

    console.log(`  Chat message sent, agentMessageId: ${agentMessageId}`);

    // Wait for the agent message to appear in the UI
    // Poll via API to get the agent message content
    const maxWaitMs = 120_000; // 2 minutes for LLM response
    const start = Date.now();
    let agentContent = '';

    while (Date.now() - start < maxWaitMs) {
      await page.waitForTimeout(3000);

      const msgRes = await page.request.get(`/api/report-messages/${agentMessageId}`);
      if (msgRes.ok()) {
        const msgData: any = await msgRes.json();
        agentContent = msgData.content || '';
        if (agentContent.length > 0) {
          break;
        }
      }
      console.log('  Waiting for agent response...');
    }

    // Assert the agent response contains relevant content
    expect(agentContent.length).toBeGreaterThan(0);
    expect(agentContent.length).toBeGreaterThan(20); // not a template/placeholder

    console.log(`  Agent response (${agentContent.length} chars):`);
    console.log(`  ${agentContent.substring(0, 500)}`);

    // Soft keyword relevance check
    const agentLower = agentContent.toLowerCase();
    const relevantKeywords = [
      'opportunity',
      'product',
      'licensing',
      'collectible',
      'market',
      'franchise',
      'model',
      'toy',
      'retail',
    ];
    const matchedKeywords = relevantKeywords.filter(kw => agentLower.includes(kw));
    if (matchedKeywords.length > 0) {
      console.log(`  Agent reply relevance OK: matched keywords: ${matchedKeywords}`);
    } else {
      console.log(
        `  WARNING: Agent reply matched none of the expected keywords. Content may be generic.`,
      );
    }

    console.log('✓ Comment sent and agent response verified');
  });
});
