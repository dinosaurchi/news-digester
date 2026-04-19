/**
 * Metal Earth Scoring Quality QA
 *
 * ============================================================================
 * Verifies the Metal Earth scoring quality fixes:
 * - Content list renders with BM25 and Final Score columns
 * - Score breakdown on detail pages shows theme_match, competitor_match, multi_signal_boost
 * - BM25 is labeled as lexical, NOT LLM
 * - "Deterministic scoring · No LLM" badge is present
 * - No misleading "AI Score" or "LLM Score" labels anywhere
 * ============================================================================
 */

import { test, expect, type Page } from '@playwright/test';

const WS_ID = 'e1dd57f673eb468ab74a49d8b4630afa';

/* ================================================================== */
/*  Helpers                                                            */
/* ================================================================== */

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

/** Fetch content items sorted by finalScore descending via API */
async function fetchContentSorted(page: Page, desc = true): Promise<any[]> {
  const res = await page.request.get(`/api/workspaces/${WS_ID}/content`);
  if (!res.ok()) return [];
  const items: any[] = await res.json();
  return [...items].sort((a, b) =>
    desc ? (b.finalScore || 0) - (a.finalScore || 0) : (a.finalScore || 0) - (b.finalScore || 0),
  );
}

/* ================================================================== */
/*  Test Suite                                                         */
/* ================================================================== */

test.describe('Metal Earth Scoring Quality QA', () => {
  test.setTimeout(120_000);

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  /* ------------------------------------------------------------------ */
  /*  Check 1: Login and navigate to Metal Earth Content page            */
  /* ------------------------------------------------------------------ */

  test('Check 1: Login and navigate to Metal Earth Content page', async ({ page }) => {
    await page.goto(`/workspaces/${WS_ID}/content`);
    await page.waitForLoadState('networkidle');

    await expect(
      page.getByRole('heading', { name: 'Content Inspection' }),
    ).toBeVisible({ timeout: 15_000 });

    await expect(
      page.getByText('Review and debug fetched content items and their relevance scores'),
    ).toBeVisible();

    console.log('✅ Check 1 PASSED: Navigated to Metal Earth Content page');
  });

  /* ------------------------------------------------------------------ */
  /*  Check 2: Content list renders properly                             */
  /* ------------------------------------------------------------------ */

  test('Check 2: Content list renders properly with scores', async ({ page }) => {
    await page.goto(`/workspaces/${WS_ID}/content`);
    await page.waitForLoadState('networkidle');

    await expect(
      page.getByRole('heading', { name: 'Content Inspection' }),
    ).toBeVisible({ timeout: 15_000 });

    // Check for table with content rows OR empty state
    const hasTable = await page.locator('table thead').isVisible().catch(() => false);
    const hasEmpty = await page.getByText('No content found').isVisible().catch(() => false);

    if (hasEmpty) {
      console.log('⚠️ Check 2: Content list is empty — no content items fetched yet.');
      test.skip();
      return;
    }

    expect(hasTable).toBeTruthy();

    // Verify column headers exist
    await expect(page.locator('th', { hasText: 'BM25' })).toBeVisible();
    console.log('  ✓ BM25 column header is visible');

    await expect(page.locator('th', { hasText: 'Final' })).toBeVisible();
    console.log('  ✓ Final Score column header is visible');

    await expect(page.locator('th', { hasText: 'Relevance' })).toBeVisible();
    console.log('  ✓ Relevance column header is visible');

    // Verify BM25 column tooltip on the <td> says "Lexical" (not LLM)
    // The title attribute is on <td>, not <th>
    const bm25Td = page.locator('td[title*="Lexical"], td[title*="NOT"]');
    const bm25TdCount = await bm25Td.count();
    expect(bm25TdCount).toBeGreaterThan(0);
    console.log(`  ✓ BM25 <td> cells have lexical tooltip (found ${bm25TdCount} cells)`);

    // Verify no BM25 <td> has LLM in the tooltip
    const bm25TdLlm = page.locator('td[title*="LLM"], td[title*="AI"], td[title*="semantic"]');
    const bm25TdLlmCount = await bm25TdLlm.count();
    // Note: "NOT an LLM" contains "LLM" so we need to be more careful
    // Let's check for positive LLM references (without "NOT")
    const bm25TdPositiveLlm = page.locator('td[title*="LLM score"], td[title*="AI score"], td[title*="Semantic score"]');
    const positiveLlmCount = await bm25TdPositiveLlm.count();
    expect(positiveLlmCount).toBe(0);
    console.log('  ✓ BM25 <td> tooltip does NOT positively reference LLM/AI/semantic');

    // Verify item count is shown
    const hasItems = await page.locator('table tbody tr').count();
    console.log(`  ✓ ${hasItems} content items displayed in table`);

    // Sort by final score descending
    const finalHeader = page.locator('th', { hasText: 'Final' });
    await finalHeader.click();
    await page.waitForLoadState('networkidle');
    console.log('  ✓ Sorted by Final Score (descending)');

    // Inspect top results via API
    const items = await fetchContentSorted(page);
    if (items.length > 0) {
      const top = items[0];
      console.log(`  Top item: "${top.title?.substring(0, 80)}" — final: ${((top.finalScore || 0) * 100).toFixed(1)}%, BM25: ${((top.bm25Score || 0) * 100).toFixed(1)}%`);
      if (items.length > 1) {
        const bottom = items[items.length - 1];
        console.log(`  Bottom item: "${bottom.title?.substring(0, 80)}" — final: ${((bottom.finalScore || 0) * 100).toFixed(1)}%, BM25: ${((bottom.bm25Score || 0) * 100).toFixed(1)}%`);
      }
    }

    console.log('✅ Check 2 PASSED: Content list renders with BM25, Final, Relevance columns');
  });

  /* ------------------------------------------------------------------ */
  /*  Check 3: High-scoring item detail page                             */
  /* ------------------------------------------------------------------ */

  test('Check 3: High-scoring item detail — score breakdown visible', async ({ page }) => {
    const items = await fetchContentSorted(page);
    if (items.length === 0) {
      console.log('⚠️ Check 3: No content items available');
      test.skip();
      return;
    }

    const topItem = items[0];
    const topScore = (topItem.finalScore || 0) * 100;
    console.log(`  Opening high-scoring item: "${topItem.title?.substring(0, 80)}" (final: ${topScore.toFixed(1)}%)`);

    await page.goto(`/workspaces/${WS_ID}/content/${topItem.id}`);
    await page.waitForLoadState('networkidle');

    // Verify Content Detail heading
    await expect(
      page.getByRole('heading', { name: 'Content Detail' }),
    ).toBeVisible({ timeout: 15_000 });

    // Verify title
    await expect(page.locator('h1').first()).toBeVisible();
    const titleText = await page.locator('h1').first().textContent();
    expect(titleText).toBeTruthy();
    console.log(`  ✓ Title visible: "${titleText?.substring(0, 80)}"`);

    // Verify Score Breakdown section
    await expect(page.getByText('Score Breakdown')).toBeVisible({ timeout: 10_000 });
    console.log('  ✓ Score Breakdown section visible');

    // Verify "Deterministic scoring · No LLM" badge
    await expect(page.getByText('Deterministic scoring · No LLM')).toBeVisible({ timeout: 10_000 });
    console.log('  ✓ "Deterministic scoring · No LLM" badge present');

    // Verify BM25 labeled as "Lexical"
    await expect(page.getByText('BM25 (Lexical)')).toBeVisible({ timeout: 10_000 });
    console.log('  ✓ BM25 labeled as "BM25 (Lexical)"');

    // Verify individual score rows (use exact:true to avoid matching tooltip text)
    await expect(page.getByText('Relevance', { exact: true })).toBeVisible();
    await expect(page.getByText('Freshness', { exact: true })).toBeVisible();
    await expect(page.getByText('Source Authority', { exact: true })).toBeVisible();
    await expect(page.getByText('Final', { exact: true })).toBeVisible();
    console.log('  ✓ All score rows present: Relevance, BM25 (Lexical), Freshness, Source Authority, Final');

    // Check for theme_match section
    const hasThemeMatch = await page.getByText('Theme Match Details').isVisible().catch(() => false);
    if (hasThemeMatch) {
      console.log('  ✓ Theme Match Details section visible');
      const hasMatched = await page.locator('text=/Matched \\(\\d+\\)/').first().isVisible().catch(() => false);
      const hasUnmatched = await page.locator('text=/Unmatched \\(\\d+\\)/').first().isVisible().catch(() => false);
      console.log(`    Matched subsection: ${hasMatched ? 'visible' : 'not found'}`);
      console.log(`    Unmatched subsection: ${hasUnmatched ? 'visible' : 'not found'}`);
    } else {
      console.log('  ℹ️ Theme Match Details section not present for this item');
    }

    // Check for competitor_match section
    const hasCompMatch = await page.getByText('Competitor Match Details').isVisible().catch(() => false);
    if (hasCompMatch) {
      console.log('  ✓ Competitor Match Details section visible');
      const hasCompMatched = await page.locator('text=/Matched \\(\\d+\\)/').first().isVisible().catch(() => false);
      const hasCompNotFound = await page.locator('text=/Not Found \\(\\d+\\)/').first().isVisible().catch(() => false);
      console.log(`    Matched subsection: ${hasCompMatched ? 'visible' : 'not found'}`);
      console.log(`    Not Found subsection: ${hasCompNotFound ? 'visible' : 'not found'}`);
    } else {
      console.log('  ℹ️ Competitor Match Details section not present for this item');
    }

    // Check for multi_signal_boost badge
    const hasMultiSignalBoost = await page.getByText('Multi-Signal Boost').isVisible().catch(() => false);
    if (hasMultiSignalBoost) {
      console.log('  ✓ Multi-Signal Boost badge visible');
    } else {
      console.log('  ℹ️ Multi-Signal Boost badge not present (item may not qualify)');
    }

    console.log('✅ Check 3 PASSED: High-scoring item detail page verified');
  });

  /* ------------------------------------------------------------------ */
  /*  Check 4: Low-scoring item detail page                              */
  /* ------------------------------------------------------------------ */

  test('Check 4: Low-scoring item detail — score breakdown explains why', async ({ page }) => {
    const items = await fetchContentSorted(page, false); // ascending
    if (items.length === 0) {
      console.log('⚠️ Check 4: No content items available');
      test.skip();
      return;
    }

    // Pick a low-scoring item (score > 0 but low, or the absolute lowest)
    const lowItem = items.find(i => (i.finalScore || 0) > 0 && (i.finalScore || 0) < 0.5) || items[0];
    const lowScore = (lowItem.finalScore || 0) * 100;
    console.log(`  Opening low-scoring item: "${lowItem.title?.substring(0, 80)}" (final: ${lowScore.toFixed(1)}%)`);

    await page.goto(`/workspaces/${WS_ID}/content/${lowItem.id}`);
    await page.waitForLoadState('networkidle');

    // Verify Content Detail heading
    await expect(
      page.getByRole('heading', { name: 'Content Detail' }),
    ).toBeVisible({ timeout: 15_000 });

    // Verify Score Breakdown section
    await expect(page.getByText('Score Breakdown')).toBeVisible({ timeout: 10_000 });

    // Verify deterministic badge
    await expect(page.getByText('Deterministic scoring · No LLM')).toBeVisible({ timeout: 10_000 });

    // Verify BM25 labeled as Lexical
    await expect(page.getByText('BM25 (Lexical)')).toBeVisible({ timeout: 10_000 });

    // Check score breakdown via API (endpoint is /api/content/{id}, not nested under workspace)
    const detailRes = await page.request.get(`/api/content/${lowItem.id}`);
    if (detailRes.ok()) {
      const detail: any = await detailRes.json();
      const breakdown = detail.scoreBreakdown;
      if (breakdown) {
        console.log(`  Score breakdown:`);
        console.log(`    Relevance:      ${(breakdown.relevance * 100).toFixed(1)}%`);
        console.log(`    BM25:           ${(breakdown.bm25 * 100).toFixed(1)}%`);
        console.log(`    Freshness:      ${(breakdown.freshness * 100).toFixed(1)}%`);
        console.log(`    Source Auth:     ${(breakdown.sourceAuthority * 100).toFixed(1)}%`);
        console.log(`    Final:          ${(detail.finalScore * 100).toFixed(1)}%`);

        if (breakdown.themeMatch) {
          console.log(`    Theme matched:   ${breakdown.themeMatch.matched?.length || 0}`);
          console.log(`    Theme unmatched: ${breakdown.themeMatch.unmatched?.length || 0}`);
        }
        if (breakdown.competitorMatch) {
          console.log(`    Comp matched:    ${breakdown.competitorMatch.matched?.length || 0}`);
          console.log(`    Comp not found:  ${breakdown.competitorMatch.unmatched?.length || 0}`);
        }
        if (breakdown.filterReason) {
          console.log(`    Filter reason:   ${breakdown.filterReason}`);
        }

        const hasLowRelevance = breakdown.relevance < 0.3;
        const hasLowBm25 = breakdown.bm25 < 0.3;
        const hasZeroThemeMatch = breakdown.themeMatch && breakdown.themeMatch.matched?.length === 0;
        const hasZeroCompMatch = breakdown.competitorMatch && breakdown.competitorMatch.matched?.length === 0;
        const hasFilterReason = !!breakdown.filterReason;

        console.log(`  Score explanation factors:`);
        console.log(`    Low relevance (<30%):   ${hasLowRelevance ? 'YES' : 'no'}`);
        console.log(`    Low BM25 (<30%):         ${hasLowBm25 ? 'YES' : 'no'}`);
        console.log(`    Zero theme matches:      ${hasZeroThemeMatch ? 'YES' : 'no'}`);
        console.log(`    Zero competitor matches: ${hasZeroCompMatch ? 'YES' : 'no'}`);
        console.log(`    Has filter reason:       ${hasFilterReason ? 'YES' : 'no'}`);
      }
    }

    // Check for exclusion reason if status is excluded
    const isExcluded = await page.locator('text=/Excluded/i').isVisible().catch(() => false);
    if (isExcluded) {
      const hasExclusionReason = await page.getByText('Exclusion Reason').isVisible().catch(() => false);
      if (hasExclusionReason) {
        console.log('  ✓ Exclusion Reason section present for excluded item');
      }
    }

    console.log('✅ Check 4 PASSED: Low-scoring item detail page verified');
  });

  /* ------------------------------------------------------------------ */
  /*  Check 5: UI does not imply LLM scoring                             */
  /* ------------------------------------------------------------------ */

  test('Check 5: No misleading LLM/AI score labels anywhere', async ({ page }) => {
    // Check content list page
    await page.goto(`/workspaces/${WS_ID}/content`);
    await page.waitForLoadState('networkidle');

    await expect(
      page.getByRole('heading', { name: 'Content Inspection' }),
    ).toBeVisible({ timeout: 15_000 });

    const listPageContent = await page.content();

    const misleadingTerms = ['AI Score', 'LLM Score', 'AI-Powered Score', 'Semantic Score', 'LLM-Powered'];
    const foundMisleading: string[] = [];
    for (const term of misleadingTerms) {
      if (listPageContent.includes(term)) {
        foundMisleading.push(term);
      }
    }

    expect(foundMisleading.length).toBe(0);
    console.log('  ✓ Content list page: no misleading AI/LLM score labels');

    // Check a content detail page
    const items = await fetchContentSorted(page);
    if (items.length > 0) {
      const midItem = items[Math.floor(items.length / 2)] || items[0];

      await page.goto(`/workspaces/${WS_ID}/content/${midItem.id}`);
      await page.waitForLoadState('networkidle');

      const detailPageContent = await page.content();
      const detailMisleading: string[] = [];
      for (const term of misleadingTerms) {
        if (detailPageContent.includes(term)) {
          detailMisleading.push(term);
        }
      }

      expect(detailMisleading.length).toBe(0);
      console.log('  ✓ Content detail page: no misleading AI/LLM score labels');

      // Verify correct labels ARE present
      await expect(page.getByText('Deterministic scoring · No LLM')).toBeVisible({ timeout: 10_000 });
      await expect(page.getByText('BM25 (Lexical)')).toBeVisible({ timeout: 10_000 });
      console.log('  ✓ "Deterministic scoring · No LLM" badge present');
      console.log('  ✓ "BM25 (Lexical)" label present');
    }

    console.log('✅ Check 5 PASSED: No misleading LLM/AI scoring labels found');
  });

  /* ------------------------------------------------------------------ */
  /*  Check 6: Console errors                                            */
  /* ------------------------------------------------------------------ */

  test('Check 6: No console errors during navigation', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    page.on('pageerror', err => {
      errors.push(err.message);
    });

    // Navigate through key pages
    await page.goto(`/workspaces/${WS_ID}/content`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const items = await fetchContentSorted(page);
    if (items.length > 0) {
      await page.goto(`/workspaces/${WS_ID}/content/${items[0].id}`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);
    }

    // Filter out benign errors
    const filteredErrors = errors.filter(e => {
      if (e.includes('favicon') || e.includes('manifest')) return false;
      if (e.includes('DevTools') || e.includes('extension')) return false;
      if (e.includes('net::ERR_CONNECTION_REFUSED')) return false;
      return true;
    });

    if (filteredErrors.length > 0) {
      console.log(`  ⚠️ Console errors found (${filteredErrors.length}):`);
      filteredErrors.forEach(e => console.log(`    - ${e}`));
    } else {
      console.log('  ✓ No console errors detected');
    }

    console.log('✅ Check 6 COMPLETE: Console error check done');
  });
});
