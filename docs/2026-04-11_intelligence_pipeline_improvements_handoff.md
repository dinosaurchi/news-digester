# Intelligence Pipeline Improvements Handoff

**Date:** 2026-04-11
**Recommended branch base:** current `main` / current HEAD of this repository
**Primary target:** improve scoring quality, clustering tunability, LLM output validation, feedback freshness, and report-chat relevance across the intelligence pipeline

---

## Why this handoff exists

A code review of the intelligence modules identified seven high and medium impact improvements. The current pipeline works end-to-end but has hardcoded tunables, no feedback decay, no post-LLM validation, and suboptimal context selection. These improvements will make the system more accurate, configurable, and robust without changing the overall architecture.

Current state confirmed from repository:

- **Scoring weights** are hardcoded in `backend/app/services/scoring.py` (`_WEIGHTS` dict) with no per-workspace override path.
- **Feedback preferences** in `backend/app/models/preferences.py` have `created_at`/`updated_at` columns but `_compute_feedback_adjustment()` treats all preferences equally regardless of age.
- **Report generation** in `backend/app/services/report_generator.py` relies solely on prompt instructions ("do not invent facts") with no post-generation citation validation.
- **Shortlist LLM refinement** in `backend/app/services/shortlist.py` silently drops unresolvable IDs returned by the LLM and only reacts when the result set is completely empty.
- **Clustering thresholds** are hardcoded in `backend/app/services/clustering.py` (`DEFAULT_SIMILARITY_THRESHOLD = 0.7`, `DEFAULT_DOMAIN_TITLE_THRESHOLD = 0.6`) with no per-workspace override.
- **BM25 scoring** in `backend/app/services/scoring.py` uses term frequency only, with no inverse document frequency component.
- **Report chat context** in `backend/app/services/report_chat.py` selects source items by insertion order with fixed caps, not by relevance to the user's question.

---

## Locked decisions

These decisions are fixed for this work unless explicitly superseded:

- All per-workspace configuration uses the existing `WorkspaceSettings.thresholds` JSON column — no schema migrations required.
- Scoring weight overrides fall back to the current hardcoded defaults when not configured.
- Clustering threshold overrides fall back to the current hardcoded defaults when not configured.
- Feedback decay uses the existing `created_at` column on preference models — no schema changes.
- Citation validation is post-generation and advisory (log warnings) — it does not block report creation.
- Shortlist ID validation is advisory (log warnings + metadata) — it does not change the existing empty-result safeguard.
- Report chat context improvements are internal to `report_chat.py` — no API contract changes.
- BM25 IDF is computed per-batch within the scoring pipeline — no external corpus store.
- Do not commit `data/` or `.ai/tmp/`.
- `make ci` must pass before completion.
- Completion requires `make up` redeploy and real API + Web UI QA.

---

## Pass 1 — Configurable scoring weights per workspace

### Goal

Allow each workspace to override the default scoring signal weights so different customers can tune relevance ranking to their needs.

### Required work

1. In `scoring.py`, change `compute_combined_score()` to accept an optional `weight_overrides: dict[str, float] | None` parameter. When provided, merge overrides into the default `_WEIGHTS` dict (unknown keys ignored, missing keys use defaults).
2. In `score_content_items()`, read `scoring_weights` from `workspace.settings.thresholds` and pass it to `compute_combined_score()`.
3. Ensure the score breakdown JSON records which weights were actually used (defaults vs overrides) for transparency.

### Files to modify

- `backend/app/services/scoring.py`

### Implementation notes

- The `WorkspaceSettings.thresholds` JSON column already exists and is used for `min_relevance_score`, `maxArticlesPerReport`, and `trusted_domains`. Add `scoring_weights` as a new key in the same dict.
- Example thresholds value after this pass:
  ```json
  {
    "min_relevance_score": 0.1,
    "maxArticlesPerReport": 15,
    "trusted_domains": ["reuters.com"],
    "scoring_weights": {
      "keyword": 0.30,
      "competitor_mention": 0.25,
      "freshness": 0.15,
      "source_authority": 0.15,
      "bm25": 0.15
    }
  }
  ```
- Weight values must be non-negative floats. Do not normalize — the caller is responsible for choosing weights that sum to 1.0. Document this in the docstring.
- Do not add API endpoints for editing weights in this pass. Weights are set via existing workspace settings update flow.

### Pass 1 acceptance criteria

- `compute_combined_score()` accepts and applies weight overrides.
- `score_content_items()` reads `scoring_weights` from workspace settings and passes them through.
- When no overrides are configured, behavior is identical to current defaults.
- The `score_breakdown_json` on each item shows the weights that were actually used.
- Existing tests in `test_scoring.py` still pass.

---

## Pass 2 — Feedback preference time decay

### Goal

Make older feedback preferences contribute less to scoring so that the system naturally adapts as user interests evolve.

### Required work

1. In `scoring.py`, add a `_compute_decay_factor(updated_at: datetime, half_life_days: float = 30.0) -> float` function that returns an exponential decay multiplier between 0.0 and 1.0 based on the age of the preference.
2. Update `_load_feedback_signals()` to return preference rows (not just aggregated weights) so that `updated_at` timestamps are available.
3. Update `_compute_feedback_adjustment()` to apply the decay factor to each preference's weight before computing the adjustment.
4. Log decayed weights for traceability in the score breakdown feedback info.

### Files to modify

- `backend/app/services/scoring.py`

### Implementation notes

- Decay formula: `factor = 2 ** (-(age_days / half_life_days))` where `age_days = (now - updated_at).days`.
- A preference updated today has factor ~1.0. A preference 30 days old has factor ~0.5. A preference 90 days old has factor ~0.125.
- Use `updated_at` as the reference timestamp (falls back to `created_at` if `updated_at` is null).
- The half-life could later be made configurable per workspace via thresholds, but for this pass use 30 days as a hardcoded default.
- This changes the effective weight of old preferences but does not delete them. Old preferences still appear in the breakdown — just with reduced influence.

### Pass 2 acceptance criteria

- A preference updated today contributes its full weight to scoring.
- A preference 30 days old contributes approximately half its weight.
- A preference 90+ days old contributes negligibly.
- The score breakdown JSON includes `decayed_weight` for each matched preference.
- When no preferences exist, behavior is identical to current.
- Existing tests in `test_scoring.py` still pass (update if necessary to account for decay).

---

## Pass 3 — Post-generation citation validation

### Goal

Validate that URLs cited in LLM-generated report markdown actually exist in the source items, catching hallucinated links before they reach the user.

### Required work

1. In `report_generator.py`, add a `_validate_citations(markdown: str, source_items: list[ContentItem]) -> dict` function that:
   - Extracts all markdown links (`[text](url)`) from the generated report.
   - Compares each URL against the URLs in the source items (use normalized URL comparison from `dedup.normalize_url`).
   - Returns a validation summary: `{"total_links": int, "grounded": int, "ungrounded": int, "ungrounded_urls": list[str]}`.
2. Call `_validate_citations()` after `_generate_via_llm()` returns.
3. Log a warning for each ungrounded citation with the URL.
4. Include the validation summary in the report's `metadata_json`.

### Files to modify

- `backend/app/services/report_generator.py`

### Implementation notes

- Use `re.findall(r'\[([^\]]*)\]\(([^)]+)\)', markdown)` to extract links.
- Normalize both the extracted URL and source item URLs via `dedup.normalize_url()` before comparison.
- This is advisory only — do not strip or reject ungrounded links. The metadata and logs allow operators to monitor hallucination rates and tune prompts over time.
- Do not fail the report generation for ungrounded citations. The report is still created and published.

### Pass 3 acceptance criteria

- All markdown links in generated reports are extracted and validated against source item URLs.
- Ungrounded citations are logged as warnings.
- The report `metadata_json` includes a `citation_validation` key with the summary.
- When all citations are grounded, no warnings are logged.
- When the LLM produces no links, validation still runs and reports `total_links: 0`.
- Existing tests in `test_report_generator.py` still pass.

---

## Pass 4 — Shortlist LLM response ID validation

### Goal

Detect and log when the LLM returns item IDs that don't exist in the input set, providing visibility into LLM response quality.

### Required work

1. In `shortlist.py` `_refine_via_llm()`, after matching LLM-selected items back to ContentItem objects:
   - Compute the set of IDs returned by the LLM.
   - Compute the set of IDs that resolved to known items.
   - Compute the set of unresolved IDs (returned by LLM but not in input).
   - Log a warning for each unresolved ID.
2. Include validation stats in the logger output: `"LLM shortlist: %d requested, %d resolved, %d unresolved"`.
3. The existing empty-result safeguard remains unchanged.

### Files to modify

- `backend/app/services/shortlist.py`

### Implementation notes

- This is purely observability — do not change the control flow or the fallback logic.
- The unresolved IDs may indicate prompt issues, model drift, or response format bugs. Logging them enables diagnosis.
- Keep the log level at WARNING for unresolved IDs so they surface in standard log monitoring.

### Pass 4 acceptance criteria

- When the LLM returns all valid IDs, no warnings are logged (only an info-level summary).
- When the LLM returns some invalid IDs, each is logged at WARNING level.
- The info-level summary always shows requested/resolved/unresolved counts.
- The existing empty-result safeguard behavior is unchanged.
- Existing tests in `test_shortlist.py` still pass.

---

## Pass 5 — Configurable clustering thresholds per workspace

### Goal

Allow each workspace to override the default clustering similarity and domain-title thresholds.

### Required work

1. In `clustering.py` `cluster_content_items()`, read `clustering_similarity_threshold` and `clustering_domain_title_threshold` from workspace settings thresholds and use them as the `similarity_threshold` and `domain_title_threshold` parameters.
2. The function already accepts these as keyword arguments — the change is in the caller passing workspace-configured values.
3. In `pipeline.py`, pass the workspace when calling `cluster_content_items()` so it can read settings.

### Files to modify

- `backend/app/services/clustering.py`
- `backend/app/services/pipeline.py` (if the workspace is not already passed to the clustering call)

### Implementation notes

- Example thresholds value after this pass:
  ```json
  {
    "clustering_similarity_threshold": 0.65,
    "clustering_domain_title_threshold": 0.55
  }
  ```
- When keys are absent, fall back to `DEFAULT_SIMILARITY_THRESHOLD` (0.7) and `DEFAULT_DOMAIN_TITLE_THRESHOLD` (0.6).
- Do not change the clustering algorithm itself — only the threshold inputs.

### Pass 5 acceptance criteria

- When workspace thresholds include clustering overrides, those values are used.
- When workspace thresholds do not include clustering overrides, current defaults are used.
- Existing tests in `test_clustering.py` still pass.
- The clustering step in the pipeline passes workspace-configured thresholds.

---

## Pass 6 — BM25 with IDF component

### Goal

Improve BM25 scoring discrimination by adding inverse document frequency so that common terms across all items contribute less to relevance than rare, specific terms.

### Required work

1. In `scoring.py`, add a `compute_document_frequencies(items_texts: list[str], query_terms: list[str]) -> dict[str, float]` function that:
   - For each query term, counts how many item texts contain that term (case-insensitive).
   - Returns `{term: idf}` where `idf = log(N / (1 + df))` and `N` is total items, `df` is document frequency.
2. Update `compute_bm25_score()` to accept an optional `idf: dict[str, float] | None` parameter. When provided, multiply each term's `log(1 + tf)` by its IDF value before averaging.
3. In `score_content_items()`, compute document frequencies once for the batch and pass them to each `compute_bm25_score()` call.

### Files to modify

- `backend/app/services/scoring.py`

### Implementation notes

- IDF is computed per scoring batch (all items in the current pipeline run), not across historical data. This keeps the computation local and avoids needing a persistent corpus index.
- When `idf` is None (e.g., in unit tests or single-item scoring), behavior is identical to current TF-only mode.
- The IDF values should be included in the score breakdown for transparency.
- Cap the final BM25 score at 1.0 as before.

### Pass 6 acceptance criteria

- `compute_document_frequencies()` correctly computes IDF for given query terms across a batch.
- `compute_bm25_score()` uses IDF when provided, falls back to TF-only when not.
- `score_content_items()` computes batch IDF and passes it through.
- Common terms (appearing in most items) contribute less than rare terms.
- The score breakdown includes IDF values.
- Existing tests in `test_scoring.py` still pass (update as needed).

---

## Pass 7 — Smarter report-chat context selection

### Goal

Prioritize source items relevant to the user's question when building report-chat context, so the LLM gets the most useful information within the context budget.

### Required work

1. In `report_chat.py`, add a `_rank_source_items_by_relevance(question: str, items: list[ContentItem]) -> list[ContentItem]` function that:
   - Tokenizes the question into keywords (lowercase, split on whitespace, remove stop words).
   - For each source item, computes a lightweight relevance score based on keyword overlap with `title + summary_snippet + raw_text[:500]`.
   - Returns items sorted by relevance score descending, with ties broken by original order.
2. In `load_report_chat_source_items()` or the caller, apply this ranking before the `limit` cap so the most relevant items are kept.
3. When the question has no meaningful keywords (e.g., "thanks" or "ok"), fall back to the current insertion-order behavior.

### Files to modify

- `backend/app/services/report_chat.py`

### Implementation notes

- This is a lightweight heuristic, not a semantic search. Token overlap (Jaccard or simple hit count) is sufficient.
- Reuse `token_overlap_similarity` from `dedup.py` if appropriate, or use a simple keyword hit count.
- A minimal stop word list is sufficient: `{"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for", "of", "and", "or", "but", "not", "this", "that", "it", "with", "from", "by", "as", "be", "has", "had", "have", "do", "does", "did", "will", "would", "can", "could", "should", "may", "might"}`.
- Do not change the `MAX_CHAT_SOURCE_ITEMS` or `MAX_SOURCE_TEXT_CHARS` constants — only the selection order.

### Pass 7 acceptance criteria

- When a user asks about a specific topic, source items related to that topic are prioritized in the context.
- When a user's question has no meaningful keywords, behavior is identical to current.
- The total number of source items and text caps remain unchanged.
- Existing tests in `test_report_chat.py` still pass.

---

## Pass 8 — Update tests for all changes

### Goal

Ensure all new and modified logic has test coverage and `make ci` passes.

### Required work

1. **test_scoring.py** — Add tests for:
   - Configurable scoring weight overrides (pass 1).
   - Feedback decay factor computation and application (pass 2).
   - BM25 with IDF vs without IDF (pass 6).
   - Ensure existing tests still pass with updated function signatures.

2. **test_report_generator.py** — Add tests for:
   - Citation validation with all-grounded links (pass 3).
   - Citation validation with ungrounded links (pass 3).
   - Citation validation with no links (pass 3).

3. **test_shortlist.py** — Add tests for:
   - LLM returning all valid IDs (pass 4).
   - LLM returning some invalid IDs — verify warning is logged (pass 4).
   - LLM returning no valid IDs — verify fallback still works (pass 4).

4. **test_clustering.py** — Add tests for:
   - Clustering with custom thresholds (pass 5).
   - Clustering with default thresholds when not configured (pass 5).

5. **test_report_chat.py** — Add tests for:
   - Source item ranking by question relevance (pass 7).
   - Fallback to insertion order for empty/trivial questions (pass 7).

### Files to modify

- `backend/app/tests/test_scoring.py`
- `backend/app/tests/test_report_generator.py`
- `backend/app/tests/test_shortlist.py`
- `backend/app/tests/test_clustering.py`
- `backend/app/tests/test_report_chat.py`

### Implementation notes

- Mock the OpenCode client boundary where needed — do not require live LLM for unit tests.
- For citation validation tests, construct synthetic markdown with known links and verify extraction/comparison.
- For decay tests, use fixed timestamps to make assertions deterministic.
- Run `make ci` at the end to verify everything passes together.

### Pass 8 acceptance criteria

- All new functions from passes 1-7 have at least one positive and one negative test case.
- All pre-existing tests still pass.
- `make ci` passes.

---

## Pass 9 — Redeploy with `make up`

### Goal

Prove the updated implementation deploys cleanly through the normal local path.

### Required commands

```bash
make ci
make up
docker compose ps
```

### Required work

1. Run `make ci` and confirm it passes.
2. Run `make up` and confirm all containers start successfully.
3. Run `docker compose ps` and confirm all required services are present and healthy.
4. Check backend logs for any startup errors related to the changes.

### Pass 9 acceptance criteria

- `make ci` passes with all new and existing tests.
- `make up` completes successfully.
- `docker compose ps` shows all required services running (app, backend, worker, beat, db, redis, opencode services).
- No startup errors in backend logs related to scoring, clustering, shortlist, report generation, or report chat changes.

---

## Pass 10 — API QA on the deployed stack

### Goal

Prove the intelligence pipeline improvements work through the deployed API.

### API QA checklist

Use the deployed stack, not test runners.

1. `GET /api/health` returns healthy status.
2. `POST /api/session/login` works with the configured admin user.
3. `GET /api/session/me` confirms authenticated session.
4. Open or create a workspace with a configured profile (priority_themes, competitors, excluded_topics).
5. Optionally set custom `scoring_weights` and/or `clustering_similarity_threshold` in workspace settings thresholds via the settings API.
6. Add at least one valid feed.
7. Trigger `POST /api/workspaces/{workspace_id}/run-now`.
8. Confirm run detail shows all pipeline steps completed:
   - Scoring step uses configured weights (or defaults). Check a content item's `score_breakdown_json` to verify weights match.
   - Clustering step completes.
   - Shortlist step completes with LLM refinement.
   - Report generation step completes.
9. Check a generated report's `metadata_json` for the `citation_validation` key — confirm it exists and shows link counts.
10. Send a report-thread chat message about a specific topic mentioned in the report. Confirm the assistant response is grounded in relevant sources.
11. If feedback preferences exist, confirm score breakdowns show `decayed_weight` entries.

### Pass 10 acceptance criteria

- API QA demonstrates healthy auth, workspace, run, report, and report-chat flows.
- Score breakdown JSON reflects configurable weights (custom or default).
- Report metadata includes citation validation summary.
- Report chat responses are grounded in source items.
- No 5xx errors during normal operation.
- Evidence from the deployed API is recorded.

---

## Pass 11 — Web UI QA on the deployed stack

### Goal

Prove the user-facing Web UI works correctly with the intelligence pipeline improvements.

### Web UI QA checklist

Use the browser against the deployed app at `http://localhost:3000`.

1. Log in with the configured admin user.
2. Create or open a workspace.
3. Configure workspace profile with priority themes, competitors, and excluded topics.
4. Add/test feeds from the UI.
5. Trigger `run-now` from the UI.
6. Open the run detail view and confirm all pipeline steps (scoring, clustering, shortlist, report) are shown as completed.
7. Open the generated report thread and verify the report content is present with properly formatted citations (markdown links, not bare URLs).
8. Trigger regenerate from the UI and verify a new report message appears.
9. Send a report-thread question about a specific topic from the report and verify the assistant reply is relevant and grounded.
10. Verify no UI errors or broken states during the above flows.

### Pass 11 acceptance criteria

- The main user flows work from the deployed Web UI.
- Run detail shows completed pipeline steps.
- Reports contain properly formatted markdown with citation links.
- Report chat responds with relevant, grounded answers.
- Report regenerate works.
- The Web UI does not display errors or broken states during normal operation.

---

## Overall acceptance criteria

The work is complete only when all of the following are true:

1. Scoring weights are configurable per workspace via `WorkspaceSettings.thresholds["scoring_weights"]`, falling back to current defaults.
2. Feedback preferences apply exponential time decay (30-day half-life) so older preferences contribute less.
3. Generated reports include post-generation citation validation in `metadata_json` with grounded/ungrounded link counts.
4. Shortlist LLM refinement logs warnings for unresolvable IDs and includes validation stats.
5. Clustering thresholds are configurable per workspace via `WorkspaceSettings.thresholds`, falling back to current defaults.
6. BM25 scoring includes an IDF component computed per batch, improving discrimination for common vs rare terms.
7. Report chat context selection prioritizes source items relevant to the user's question.
8. All changes have test coverage and `make ci` passes.
9. `make up` redeploy is completed and verified on the deployed stack.
10. Full-stack API QA on the deployed stack demonstrates the intended behavior.
11. Full-stack Web UI QA on the deployed stack demonstrates the intended behavior.

---

## Known implementation risks to watch

- The `thresholds` JSON column is schemaless — malformed values could cause runtime errors. Validate and log clearly when parsing overrides; always fall back to defaults on bad input.
- Feedback decay changes effective scores for workspaces with old preferences — existing score distributions will shift. This is intended but worth noting in case QA results look different from previous runs.
- Citation validation regex may miss edge cases in markdown link syntax (nested brackets, encoded URLs). Keep the regex simple and document known limitations.
- BM25 IDF computation adds O(items x query_terms) work to the scoring step. For typical batch sizes (50-500 items) this is negligible, but log timing if batches grow large.
- Report chat keyword ranking is a heuristic — it improves average case but may occasionally deprioritize a relevant item if the user's question uses different vocabulary than the source. This is acceptable for this pass; semantic search can be added later.

---

## Recommended execution order

1. Pass 1: Configurable scoring weights
2. Pass 2: Feedback time decay
3. Pass 3: Citation validation
4. Pass 4: Shortlist ID validation
5. Pass 5: Configurable clustering thresholds
6. Pass 6: BM25 with IDF
7. Pass 7: Smarter report-chat context
8. Pass 8: Tests
9. Pass 9: Redeploy
10. Pass 10: API QA
11. Pass 11: Web UI QA

Passes 1-2 are foundational scoring changes and should land first. Passes 3-4 are independent validation improvements. Passes 5-7 are independent of each other. Pass 8 covers all test updates. Passes 9-11 are deployment verification.

---

## Current verification status at handoff creation

This handoff document was written after confirming the repository state encodes the hardcoded values and missing features described above. The implementation described here has **not** yet been completed by this document alone. The follow-on engineer must execute the passes above and then prove the result with redeploy and QA.
