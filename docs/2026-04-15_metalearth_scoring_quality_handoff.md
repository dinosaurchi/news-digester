# Metal Earth Scoring Quality Repair — Multi-Pass Handoff

## Goal

Raise the quality and usefulness of content scoring for the Metal Earth workspace and similar customer setups.

This work should address three distinct problems that are currently mixed together:

1. **Feed/query noise**: broad Google News search feeds pull many weak or irrelevant articles.
2. **Literal scoring**: the current scoring pipeline is mostly lexical and phrase-based, so realistic relevant articles often score lower than operators expect.
3. **Product expectation mismatch**: the UI now shows `bm25`/`bm25Score`, but the system still does **not** use an LLM to read articles and assign content scores.

The follow-on engineer should fix these explicitly and prove the result with tests, redeploy, and deployed-stack QA.

---

## Current state confirmed from the repository and deployed stack

### 1. Content scoring is not LLM-based

The content scoring pipeline in `backend/app/services/scoring.py` computes:

- `keyword`
- `competitor_mention`
- `freshness`
- `source_authority`
- `bm25`
- `content_type_prior`

It then combines them via weighted sum.

Confirmed in:

- `backend/app/services/scoring.py:914-952`
- `backend/app/services/scoring.py:339-345`

The LLM is only used later for:

- shortlist reranking in `backend/app/services/shortlist.py`
- report generation in `backend/app/services/report_generator.py`

This means any plan that expects article relevance scoring to improve by itself because OpenCode/LLM is enabled is incorrect. That wiring does not exist today.

### 2. Live Metal Earth scores are genuinely low

Observed on deployed workspace `e1dd57f673eb468ab74a49d8b4630afa`:

- item count: `135`
- average final score: `0.1751`
- median final score: `0.1571`
- max final score: `0.4123`
- `93/135` items are below `0.2`
- `130/135` items are below `0.3`

The BM25 signal is not completely broken:

- average `bm25Score`: `0.4363`
- max `bm25Score`: `1.0`

So the problem is not simply “BM25 is zero everywhere”. The final weighted score is still low for most items.

### 3. Feed/query noise is materially contributing

The Metal Earth real-feed QA setup in:

- `e2e/metalearth-real-flow.spec.ts`
- `tests/manual/opencode_full_flow_metalearth_real_feeds.py`

uses broad Google News search feeds such as:

- `Tenyo`
- `licensing deal`
- `model kit brand`
- `toy fair collectibles`

These produce obvious junk and weakly related results.

Observed examples from deployed content:

- multiple unrelated `Tenyo Kosev` motorcycle death articles
- unrelated pharma/licensing articles from the generic licensing feed

This confirms the feed set is not precise enough.

### 4. The current workspace settings make noise visible instead of filtered

The Metal Earth QA flows set:

- `minRelevanceScore = 0.0`
- `minFinalScore = 0.0`

in:

- `e2e/metalearth-real-flow.spec.ts`
- `tests/manual/opencode_full_flow_metalearth_real_feeds.py`

This is fine for debugging ingestion breadth, but it guarantees operators will see a lot of low-scoring content in the Content page.

### 5. The current lexical/profile matching is too rigid

Current scoring characteristics:

- `compute_keyword_score()` checks whether each full priority-theme string appears as a substring.
- `compute_competitor_mention_score()` checks whether each full competitor string appears as a substring.
- `compute_bm25_score()` is token-based and helps, but it still relies on surface-form overlap.
- `compute_source_authority_score()` returns `0.5` when no trusted domains are configured, so source quality is barely distinguished in the Metal Earth workspace today.

This means long profile phrases like:

- `licensed merchandise and IP deals`
- `Tenyo Metallic Nano (Japanese licensee, same factory)`
- `hobby retail channel and specialty store trends`

are not good direct matching keys.

---

## Root-cause summary

The low score problem is caused by a combination of:

1. **Noisy feeds** pulling weakly related content.
2. **Low thresholds** exposing all content to operators.
3. **Profile strings being used directly as lexical matching keys** without normalization.
4. **A deterministic lexical scoring algorithm** that does not understand semantics.
5. **No LLM scoring stage**, despite likely operator expectation that the system is “AI-reading” the articles.

This is **not** primarily a “bad source authority” issue today, because the current workspace has no trusted-domain configuration and the scorer assigns most sources the same neutral `0.5`.

---

## Non-negotiable requirements

- Keep the current pipeline fail-fast. Do not silently degrade or hide broken scoring stages.
- Add unit tests for every scoring/feed/profile normalization change.
- Keep deterministic scoring stable enough for reproducible tests.
- `make ci` must pass after every implementation pass.
- Completion requires:
  - `make up` redeploy
  - API QA against the deployed stack
  - Web UI QA against the deployed stack
- Do not commit data from `data/`.
- Do not rely only on mocked tests; deployed-stack QA is required before calling the work complete.

---

## Locked decisions

These decisions are fixed for this work unless explicitly superseded later.

1. **Do not replace deterministic scoring with pure LLM scoring.**
   Use deterministic scoring as the primary ranking layer.

2. **If LLM scoring is added, it must be a bounded secondary signal or rerank stage.**
   It must not silently become mandatory for the entire content scoring pipeline without explicit product decision.

3. **Feed/query quality must be fixed before adding semantic scoring.**
   Better scoring on bad feeds still produces bad operator experience.

4. **Profile normalization must be implemented.**
   Raw long-form competitor/theme strings are not acceptable direct matching keys.

5. **The Content page should remain explainable.**
   Operators need to understand why an item scored low or high.

6. **The Metal Earth QA flows should remain real-feed, deployed-stack flows.**
   They are allowed to evolve, but they must continue to exercise the actual deployed product.

---

## Scope boundaries

### In scope

- Feed query hardening for the Metal Earth QA setup
- Profile normalization for themes and competitors
- Deterministic scoring quality improvements
- Optional bounded semantic/LLM-assisted scoring design and implementation
- Score-breakdown transparency improvements
- Unit tests
- Integration/API tests
- Playwright/manual QA updates
- Redeploy and deployed-stack QA

### Out of scope

- Full ML training pipeline
- Embeddings/vector database infrastructure
- Replacing Google News as the ingestion provider for all workspaces
- Human editorial workflow or manual per-item labeling UI
- Major schema redesign unless clearly necessary

---

# Pass 1 — Baseline diagnostics and scoring observability

## Goal

Make the scoring problem measurable before changing behavior.

## Why this pass exists

Right now operators can see low final scores, but the system does not provide enough aggregated diagnostics to answer:

- which feed is causing most low-quality items
- which scoring component is suppressing final scores
- which profile themes/competitors are actually matching

## Required work

1. Add a repo-local diagnostic helper for deployed-stack analysis of a workspace:
   - content count
   - per-feed score distribution
   - component distribution (`relevance`, `bm25`, `freshness`, `sourceAuthority`)
   - top unmatched themes
   - top unmatched competitors

2. Extend score breakdown or add a helper function so theme/competitor match details are inspectable from the backend for a content item.

3. Add explicit logging/metadata for:
   - normalized themes used for keyword matching
   - normalized competitor aliases used for competitor matching

## Files to modify

- `backend/app/services/scoring.py`
- optionally a new helper under `tests/manual/` or `scripts/`
- optionally `backend/app/services/content.py` if score breakdown needs enrichment

## Unit tests

Add to `backend/app/tests/test_scoring.py`:

1. `test_score_breakdown_contains_component_scores_consistently`
2. `test_score_breakdown_can_expose_theme_match_metadata`
3. `test_score_breakdown_can_expose_competitor_match_metadata`

## Pass 1 acceptance criteria

- Engineers can inspect which components produced a low score.
- Theme/competitor matching inputs are visible and testable.
- No scoring behavior changes yet unless strictly needed for observability.
- `make ci` passes.

---

# Pass 2 — Harden the Metal Earth real-feed queries

## Goal

Reduce junk ingestion from the Metal Earth QA feeds so the workspace content corpus is materially more relevant before scoring changes.

## Problems to fix

- `Tenyo` alone is too broad and produces unrelated people/news.
- generic `licensing deal` queries produce many unrelated industries.
- generic `model kit brand` / `DIY kit` queries are broad and noisy.

## Required work

1. Review and tighten feed definitions in:
   - `e2e/metalearth-real-flow.spec.ts`
   - `tests/manual/opencode_full_flow_metalearth_real_feeds.py`

2. Replace overly broad queries with more targeted versions.

Examples of expected direction:

- competitor feed:
  - from broad `Tenyo`
  - to more constrained terms like:
    - `"Tenyo Metallic Nano"`
    - `"Piececool metal model"`
    - `"UGEARS model kit"`
    - `"3D metal puzzle"`

- licensing feed:
  - from broad `licensing deal`
  - to more toy/franchise-specific combinations such as:
    - `toy licensing`
    - `consumer products licensing`
    - `collectibles licensing`
    - `franchise merchandise toys`

- hobby/model feed:
  - bias toward collectible hobby/model contexts rather than general DIY

3. Keep the real-feed setup broad enough to find relevant signals, but remove obvious junk-producing terms.

4. Update any comments/docs explaining why each feed exists and what signal it is expected to provide.

## Files to modify

- `e2e/metalearth-real-flow.spec.ts`
- `tests/manual/opencode_full_flow_metalearth_real_feeds.py`
- optionally `docs/2026-04-11_metalearth_full_flow_test_handoff.md` if it references the old feeds

## Unit tests

This pass is mostly test-fixture/config driven, but still add tests where possible:

1. `backend/app/tests/test_feeds.py`
   - add validation tests for the feed URLs if helper validation exists

2. Add a lightweight fixture-level assertion in e2e/manual helpers that the feed list no longer contains the known-bad broad query tokens:
   - bare `Tenyo`
   - bare `licensing deal`
   - bare `model kit brand`

If repo conventions make unit tests for feed strings awkward, add a small deterministic test module under `tests/` that asserts the Metal Earth feed config contains the tightened terms.

## Pass 2 acceptance criteria

- The Metal Earth QA feed set no longer contains the known junk-heavy broad terms.
- Real-feed QA setup remains operational.
- Comments/docs explain the rationale for each feed.
- `make ci` passes.

---

# Pass 3 — Normalize profile themes and competitor aliases before scoring

## Goal

Stop using raw long-form profile text directly as matching keys.

## Problems to fix

- long priority themes are poor direct substring targets
- competitor strings include explanatory parentheticals and punctuation
- exact raw strings hide obvious matches

## Required work

1. Introduce normalization helpers in `scoring.py` or a nearby helper module:
   - normalize competitor names
   - strip parenthetical annotations
   - split comma-separated theme phrases into meaningful sub-terms
   - optionally derive aliases from multi-entity phrases

2. Add deterministic alias expansion for competitors.

Examples:

- `Tenyo Metallic Nano (Japanese licensee, same factory)` should contribute aliases such as:
  - `tenyo metallic nano`
  - `metallic nano`

- `Piececool (Chinese 3D metal puzzles)` should contribute:
  - `piececool`

3. Add deterministic theme decomposition for priority themes.

Examples:

- `Star Wars, Marvel, Disney franchise developments`
  should contribute matchable units like:
  - `star wars`
  - `marvel`
  - `disney`
  - `franchise developments`

- `licensed merchandise and IP deals`
  should contribute units like:
  - `licensed merchandise`
  - `ip deals`
  - `licensing`

4. Ensure the normalization output is used by:
   - keyword score
   - BM25 query term generation
   - competitor mention score

5. Preserve raw profile values for UI display; normalization is internal scoring logic.

## Files to modify

- `backend/app/services/scoring.py`
- optionally a new helper module if the normalization becomes large

## Unit tests

Add to `backend/app/tests/test_scoring.py`:

1. `test_normalize_competitor_removes_parenthetical_noise`
2. `test_normalize_competitor_generates_expected_aliases`
3. `test_priority_theme_decomposition_generates_subterms`
4. `test_keyword_score_uses_normalized_theme_terms`
5. `test_competitor_mention_score_uses_aliases_not_only_raw_strings`
6. `test_bm25_uses_normalized_theme_terms`

## Pass 3 acceptance criteria

- Scoring no longer relies only on raw long-form profile strings.
- Competitor matches work for realistic names/aliases.
- Multi-entity priority themes can contribute through meaningful subterms.
- Existing scoring tests still pass after updates.
- `make ci` passes.

---

# Pass 4 — Improve deterministic scoring quality and weighting

## Goal

Make final scores better reflect “usefulness to the workspace” instead of looking uniformly low.

## Problems to fix

- final scores are compressed into a low band
- source authority is mostly neutral because trusted domains are not configured
- threshold configuration currently makes every weak item visible
- current weights may under-reward strong thematic matches

## Required work

1. Revisit default scoring weights in `backend/app/services/scoring.py`.

Current defaults:

- `keyword = 0.25`
- `competitor_mention = 0.20`
- `freshness = 0.20`
- `source_authority = 0.15`
- `bm25 = 0.20`

2. Decide whether the final-score distribution should remain strict or be recalibrated.

Options to evaluate:

- increase weight on theme/BM25 relevance
- reduce competitor binary dominance if it over- or under-contributes
- add mild boosting when multiple theme families match together
- keep scores bounded and explainable

3. Add a workspace-level trusted-domain configuration path for the Metal Earth QA flow if it does not already exist in those test flows.

Examples of candidate trusted domains:

- `disney.com`
- `starwars.com`
- `marvel.com`
- `hasbro.com`
- `mattel.com`
- `toybook.com`
- `licenseglobal.com`
- `anbmedia.com`
- `thepopinsider.com`

Do not hardcode Metal Earth-specific domains into global scoring logic. Use workspace settings.

4. Revisit QA workspace thresholds in the Metal Earth flows.

The current `0.0` thresholds are useful for debugging ingestion but bad for operator readability.

Implement a deliberate choice:

- either keep `0.0` for special debugging runs only
- or set a non-zero threshold for the standard Metal Earth QA flow

Recommendation:

- standard real-flow QA should use a non-zero threshold such as `0.15` or `0.20`
- if broad corpus inspection is still needed, create a separate debug/manual path

5. Add tests covering final-score distribution behavior for realistic Metal Earth-like data.

## Files to modify

- `backend/app/services/scoring.py`
- `backend/app/tests/test_scoring.py`
- `e2e/metalearth-real-flow.spec.ts`
- `tests/manual/opencode_full_flow_metalearth_real_feeds.py`

## Unit tests

Add to `backend/app/tests/test_scoring.py`:

1. `test_realistic_toy_licensing_article_scores_above_threshold`
2. `test_irrelevant_generic_licensing_article_scores_lower_than_toy_licensing_article`
3. `test_competitor_article_scores_above_generic_noise_article`
4. `test_trusted_domain_boost_improves_source_authority`
5. `test_multi_signal_article_scores_higher_than_single_signal_article`
6. `test_metalearth_regression_distribution_not_compressed_to_trivial_range`

The regression test should use a small synthetic corpus, not real network data.

## Pass 4 acceptance criteria

- Strongly relevant toy/licensing/franchise/competitor articles score materially higher than obvious weak matches.
- Source authority can differentiate trusted domains when configured.
- The standard Metal Earth QA setup no longer intentionally surfaces all junk by default.
- Final scores have a more useful spread for operators.
- `make ci` passes.

---

# Pass 5 — Add explicit semantic scoring or LLM-assisted rerank decision

## Goal

Resolve the product expectation gap around “AI scoring”.

## Why this pass exists

The current product behavior looks like an AI-driven system, but content scoring is still lexical. If semantic article understanding is required, it must be added explicitly and transparently.

## Decision gate

Choose one of the two paths and document it in code/comments/tests:

### Option A — Stay deterministic only

If deterministic scoring is sufficient after Passes 2–4:

- do not add LLM scoring
- explicitly document in product-facing comments/docs that LLM is used for shortlist/report generation, not base content scoring
- ensure UI labels and QA reflect that truth

### Option B — Add bounded semantic/LLM scoring

If semantic scoring is required:

1. Add a new optional scoring component, for example `semantic_relevance`.
2. Use the LLM only on a bounded candidate set, not on every raw ingested item.
   Recommendation:
   - deterministic prefilter first
   - LLM scoring only on top N candidates per run or per cluster
3. Require explicit failure behavior:
   - if LLM semantic scoring is enabled but unavailable, fail the semantic stage loudly
   - do not silently fabricate semantic scores
4. Store rationale and raw response metadata for debugging.
5. Expose the semantic score in the score breakdown.

## Files to modify

If Option A:

- docs/comments/tests only as needed

If Option B:

- `backend/app/services/scoring.py`
- possibly `backend/app/services/opencode_client.py`
- `backend/app/services/pipeline.py`
- content score breakdown and UI display code

## Unit tests

If Option A:

1. add explicit tests ensuring the score breakdown does not promise nonexistent LLM scoring

If Option B, add:

1. `test_semantic_scoring_component_present_when_enabled`
2. `test_semantic_scoring_not_called_for_empty_candidate_set`
3. `test_semantic_scoring_failure_fails_stage_or_is_explicitly_reported`
4. `test_final_score_includes_semantic_component_when_enabled`
5. `test_score_breakdown_exposes_semantic_component`

## Pass 5 acceptance criteria

- There is no longer ambiguity about whether content scoring is LLM-based.
- If semantic scoring is added, it is bounded, testable, explainable, and fail-fast.
- `make ci` passes.

---

# Pass 6 — API contract and score-breakdown transparency improvements

## Goal

Give operators enough explanation in the API and UI to understand why content scored low.

## Required work

1. Extend `scoreBreakdown` so it can expose:
   - normalized theme matches
   - normalized competitor matches
   - trusted-domain effect
   - threshold/filter reason
   - optional semantic score if Pass 5 Option B is chosen

2. Ensure the list/detail API surfaces what is needed for debugging without forcing direct DB inspection.

3. Update UI labels/tooltips/help copy where needed so:
   - `bm25` is clear
   - operators understand what affects final score
   - if no LLM scoring exists, the UI does not imply otherwise

## Files to modify

- `backend/app/services/content.py`
- `backend/app/schemas/content.py`
- `src/types/content.ts`
- `src/pages/ContentPage.tsx`
- `src/pages/ContentDetailPage.tsx`

## Unit tests

Add or extend:

- `backend/app/tests/test_content.py`
- `backend/app/tests/test_score_breakdown_enrichment.py`

Required tests:

1. `test_content_detail_exposes_theme_match_metadata`
2. `test_content_detail_exposes_competitor_match_metadata`
3. `test_content_detail_exposes_filter_reason_and_threshold`
4. `test_content_list_contract_matches_updated_breakdown_fields`

## Pass 6 acceptance criteria

- Operators can understand low scores from the API/UI.
- UI text does not misrepresent lexical or semantic scoring behavior.
- `make ci` passes.

---

# Pass 7 — Dedicated unit, integration, and regression tests

## Goal

Lock the scoring-quality fixes in place with stable automated coverage.

## Required work

1. Expand unit coverage in `backend/app/tests/test_scoring.py` as described in Passes 1–5.
2. Add API-level integration coverage for a realistic workspace scenario.
3. Add or update Web UI coverage for the Content page and Content detail score breakdown.

## Required automated test coverage

### Backend unit tests

- normalization helpers
- alias generation
- keyword matching with decomposed themes
- competitor matching with aliases
- source authority with trusted domains
- regression comparisons between relevant and irrelevant synthetic articles
- optional semantic scoring behavior

### API integration tests

Add a dedicated integration script or test module under `tests/integration/`, for example:

- `tests/integration/test_metalearth_scoring_api.py`

Suggested cases:

1. A strong franchise/licensing article scores above the configured threshold.
2. A generic unrelated licensing article scores lower.
3. A competitor article with normalized alias match scores above a noise article.
4. `scoreBreakdown` exposes theme/competitor/source diagnostics.
5. Content list excludes weak items when the non-zero threshold is used.

### Web UI tests

Add/update Playwright coverage:

- verify the Content list no longer surfaces a wall of obviously weak junk in the standard Metal Earth QA flow
- verify Content detail shows the relevant score-breakdown fields
- verify UI labels do not imply nonexistent LLM scoring unless Pass 5 Option B is implemented

## Pass 7 acceptance criteria

- The new behavior is protected by unit tests.
- The deployed API behavior is covered by integration-style checks.
- The Web UI behavior is covered by Playwright where practical.
- `make ci` passes.

---

# Pass 8 — Redeploy with `make up`

## Goal

Prove the repaired implementation runs on the normal deployed stack.

## Required work

1. Run:

```bash
make up
```

2. Confirm the containers are healthy:

```bash
docker compose ps
```

3. If any service fails to start, stop and fix the underlying issue before moving to QA.

## Pass 8 acceptance criteria

- `make up` succeeds.
- `docker compose ps` shows the expected running services.
- No scoring-related startup failures or silent degraded modes are introduced.

---

# Pass 9 — API QA on the deployed stack

## Goal

Validate the fixes through the real deployed API, not just tests.

## Required work

Run checks against the deployed stack after `make up`.

### 9.1 Create or reuse a Metal Earth workspace

Use the revised real-flow fixture or a purpose-built API helper.

### 9.2 Trigger a real run

Verify the run completes successfully.

### 9.3 Inspect score distributions

Use API calls to confirm:

- the standard Metal Earth flow no longer shows almost all items clustered below `0.2`
- relevant items score materially above obvious weak matches
- thresholds exclude clearly weak content if non-zero thresholding is part of the chosen design

### 9.4 Inspect representative item details

For at least:

1. one strong franchise/licensing item
2. one competitor item
3. one weak/noisy item

verify:

- `finalScore`
- `relevance`
- `bm25`
- `sourceAuthority`
- theme/competitor diagnostics
- optional semantic score if implemented

### Suggested commands

```bash
curl -sS http://localhost:3000/api/workspaces/<ws_id>/content | python -m json.tool
curl -sS http://localhost:3000/api/content/<content_id> | python -m json.tool
```

If host networking is unavailable in the environment, use the compose network path from a container as done in previous repo QA notes.

## Pass 9 acceptance criteria

- API responses show materially improved relevance separation.
- Strong items outrank weak items for understandable reasons.
- Score breakdown data is sufficient to explain outcomes.
- Any semantic scoring behavior is visible and explicit if implemented.

---

# Pass 10 — Web UI QA on the deployed stack

## Goal

Verify the operator experience on the real app at the Web UI level.

## Required work

Use the browser or Playwright against the deployed app.

### Required checks

1. Open the Metal Earth workspace Content page.
2. Confirm the page does not read like a wall of obviously weak junk for the standard QA path.
3. Sort by final score and inspect top results.
4. Open several content detail pages and verify:
   - score breakdown is understandable
   - theme/competitor/source information is visible if implemented
   - labels are accurate
   - UI does not imply nonexistent LLM scoring unless actually implemented

5. Confirm any thresholding or filtering changes behave correctly in the UI.

### Recommended Playwright coverage

Create or extend a deployed-stack Playwright flow to assert:

- content list renders
- a top-ranked item shows materially non-trivial score
- a weak/noisy item is absent or visibly lower-ranked
- content detail breakdown contains the expected fields

## Pass 10 acceptance criteria

- The Web UI reflects the intended repaired behavior.
- Operators can understand why content scored high or low.
- The Content page experience is materially better than the current baseline.

---

## Final acceptance criteria

The work is complete only when all of the following are true:

1. The Metal Earth real-feed setup no longer uses the known junk-heavy broad queries.
2. Profile themes and competitors are normalized before scoring.
3. Strongly relevant toy/licensing/franchise/competitor articles score materially higher than weak generic matches.
4. Source authority can differentiate trusted domains when configured.
5. The standard Metal Earth QA path does not intentionally surface every weak item with zero thresholds unless explicitly designated as a debug mode.
6. The product truth about semantic/LLM scoring is explicit:
   - either there is no LLM content scoring and the UI/docs say so
   - or there is bounded semantic scoring and it is exposed transparently
7. Unit tests cover the repaired logic.
8. `make ci` passes.
9. `make up` redeploy succeeds.
10. API QA on the deployed stack demonstrates the repaired behavior.
11. Web UI QA on the deployed stack demonstrates the repaired behavior.

---

## Recommended execution order

Follow this order:

1. Pass 1 — diagnostics
2. Pass 2 — feed hardening
3. Pass 3 — profile normalization
4. Pass 4 — deterministic scoring improvements
5. Pass 5 — semantic/LLM scoring decision
6. Pass 6 — API/UI transparency
7. Pass 7 — automated tests
8. Pass 8 — redeploy
9. Pass 9 — API QA
10. Pass 10 — Web UI QA

Do not jump to semantic scoring first. Fix feed quality and normalization before adding another scoring layer.

---

## Implementation notes for the next engineer

- Be disciplined about separating feed quality fixes from scoring fixes when reviewing diffs.
- Keep the scoring changes explainable. Operators need to debug score outcomes.
- Avoid hardcoding Metal Earth-specific behavior into the global scorer unless it is expressed through workspace profile/settings inputs.
- When changing scores, update tests to compare relative ordering and meaningful thresholds, not brittle exact floating-point values unless necessary.
- If a temporary diagnostic helper is created, keep it in repo-local scripts/tests/docs and do not commit generated data.
- Before closing the work, record:
  - final feed definitions used
  - workspace thresholds used
  - whether semantic/LLM scoring was implemented or explicitly deferred
  - deployed QA evidence
