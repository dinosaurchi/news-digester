# Metal Earth Scoring Quality Follow-Up Handoff

## Goal

Finish the Metal Earth scoring-quality repair by fixing the issues still left unresolved after the `chi/fix-scoring-quality` branch review.

This handoff is intentionally narrow. It does **not** restart the full scoring-quality project from scratch. It focuses on the specific gaps that prevent the previous work from being considered complete:

1. The real QA settings path is still not wired correctly end-to-end.
2. The new deployed diagnostic helper does not match the current content API contract.
3. The new tests do not yet prove the real API behavior and are not currently runnable in this environment.
4. Completion still requires redeploy and deployed-stack API + Web UI QA.

---

## Confirmed issues from branch review

### 1. Threshold and trusted-domain settings are not consistently consumed by the scorer

Observed mismatch:

- the settings API persists threshold keys in the workspace settings payload using API aliases such as:
  - `minRelevanceScore`
  - `minFinalScore`
  - potentially `trustedDomains`
- the scorer currently reads:
  - `min_relevance_score`
  - `trusted_domains`

Consequence:

- the standard Metal Earth QA path can still behave like debug mode for thresholding
- trusted-domain boosts may not apply in the Playwright real-flow path
- the tests added on the branch do not catch this, because many of them build settings dicts directly with the scorer’s preferred snake_case keys

### 2. The deployed diagnostic helper cannot work against the current list-content API

Observed mismatch:

- the diagnostic helper expects paginated content responses with an `items` field
- it also expects raw `score_breakdown_json` to be available from the content list endpoint
- the current content list endpoint returns a plain list of `ContentItemOut` objects and does not include raw score breakdown

Consequence:

- the helper cannot provide the required deployed-stack observability from the current public API shape
- Pass 1 from the original handoff is not actually complete

### 3. The new integration tests are not real API integration tests

Observed mismatch:

- `tests/integration/test_metalearth_scoring_api.py` exercises `score_content_items()` directly rather than the HTTP API
- that means it cannot detect API/schema/settings serialization bugs

Consequence:

- the most important runtime mismatch in the real settings path can slip through

### 4. The new integration test harness is not currently runnable here

Observed failure:

- `tests/integration/conftest.py` imports app modules that load settings
- current environment settings validation fails before the tests run

Consequence:

- the newly added integration tests are not yet a reliable acceptance gate

### 5. Required completion steps were not demonstrated

Still missing:

- `make ci`
- `make up`
- deployed-stack API QA
- deployed-stack Web UI QA

This work is not complete until all four are done and documented.

---

## Non-negotiable requirements

- Keep fail-fast behavior. Do not silently accept bad/missing settings keys.
- Preserve deterministic scoring as the primary content-scoring layer.
- Add unit tests for every parser/normalization/settings-contract fix.
- Add runnable integration/API tests that validate the real HTTP contract.
- Do not mark complete until:
  - `make ci` passes
  - `make up` succeeds
  - deployed-stack API QA passes
  - deployed-stack Web UI QA passes
- Do not commit data from `data/`.

---

## Scope

### In scope

- canonical threshold/settings key handling
- scorer consumption of canonical threshold/trusted-domain config
- repair of the deployed diagnostic helper
- runnable integration test harness repair
- true API integration coverage for scoring and score-breakdown behavior
- deployed-stack QA updates

### Out of scope

- replacing deterministic scoring with LLM scoring
- new model/provider integrations
- feed-provider replacement
- broad product redesign outside the scoring/debugging fixes

---

# Pass 1 — Canonicalize threshold/settings keys end-to-end

## Goal

Make workspace settings deterministic and unambiguous so the scorer reads the same threshold/trusted-domain values that the API and UI write.

## Required work

1. Define the canonical persisted shape for scoring-related workspace thresholds.

Recommended direction:

- persist canonical snake_case internally:
  - `min_relevance_score`
  - `min_final_score`
  - `max_articles_per_report`
  - `trusted_domains`
- allow API camelCase input aliases, but normalize them before persistence

2. Update workspace settings parsing/serialization so both of these input shapes are handled consistently:

- API/UI-style:
  - `minRelevanceScore`
  - `minFinalScore`
  - `maxArticlesPerReport`
  - `trustedDomains`
- internal canonical:
  - `min_relevance_score`
  - `min_final_score`
  - `max_articles_per_report`
  - `trusted_domains`

3. Ensure the scorer reads the canonical keys only after normalization.

4. Decide explicitly what to do with `min_final_score`.

One of the following must be chosen and covered by tests:

- Option A: keep `min_final_score` as a real filtering/input concept and wire it through the scoring pipeline explicitly
- Option B: remove it from this flow and document that content filtering uses `min_relevance_score` only

Do not leave `minFinalScore` present in settings fixtures if the runtime does nothing with it and nobody explains that.

## Files to modify

- `backend/app/schemas/workspace.py`
- `backend/app/api/workspaces.py`
- `backend/app/services/workspace.py`
- `backend/app/services/scoring.py`
- any workspace/settings DTO helpers used by the frontend if needed

## Required unit tests

Add or extend tests under:

- `backend/app/tests/test_settings.py`
- `backend/app/tests/test_scoring.py`

Required cases:

1. `test_put_settings_normalizes_camelcase_threshold_keys`
2. `test_put_settings_normalizes_trusted_domains_alias`
3. `test_settings_round_trip_exposes_expected_threshold_keys`
4. `test_scorer_uses_normalized_min_relevance_score_from_workspace_settings`
5. `test_scorer_uses_normalized_trusted_domains_from_workspace_settings`
6. one explicit test for the chosen `min_final_score` behavior

## Pass 1 acceptance criteria

- the scorer reads the same threshold/trusted-domain values regardless of whether the client submitted camelCase or snake_case
- the Metal Earth Playwright/manual QA paths are no longer silently bypassing threshold/trusted-domain behavior
- tests fail if key normalization regresses

---

# Pass 2 — Repair the deployed diagnostic helper and score observability path

## Goal

Provide a working deployed-stack diagnostic tool that can actually inspect score behavior from the public API.

## Required work

1. Decide how the diagnostic helper will obtain score details.

Recommended direction:

- use `/workspaces/{workspace_id}/content` for list discovery
- use `/api/content/{content_id}` detail calls for score breakdown

2. Update the helper so it matches the real API contract:

- do not assume pagination unless the API actually provides it
- do not assume `score_breakdown_json` is present on the list response
- use camelCase response fields where the public API exposes camelCase

3. Ensure the helper can produce:

- content count summary
- included/excluded counts
- per-feed or per-source distribution
- component score distribution
- top unmatched themes
- top unmatched competitors
- filter reasons / threshold behavior

4. If the current public API does not expose enough information for the intended diagnostics, add the minimum required API support explicitly and test it.

Do not rely on direct DB access for this diagnostic path.

## Files to modify

- `tests/manual/diagnostic_workspace_scores.py`
- optionally:
  - `backend/app/api/content.py`
  - `backend/app/services/content.py`
  - `backend/app/schemas/content.py`

## Required unit/integration tests

Add or extend:

- `backend/app/tests/test_content.py`
- `backend/app/tests/test_score_breakdown_enrichment.py`
- `tests/integration/test_metalearth_scoring_api.py` or a replacement HTTP-focused module

Required cases:

1. a test proving the diagnostic helper assumptions match the current API contract
2. `test_content_detail_exposes_required_score_breakdown_fields_for_diagnostics`
3. `test_content_list_and_content_detail_contract_support_workspace_diagnostics`

## Pass 2 acceptance criteria

- the diagnostic helper runs successfully against the deployed stack using only supported API responses
- engineers can inspect thresholds, trusted-domain effects, theme matches, competitor matches, and filter reasons without DB inspection

---

# Pass 3 — Replace pseudo-integration tests with true API integration coverage

## Goal

Make the automated acceptance layer catch real HTTP contract and settings-wiring regressions.

## Required work

1. Rework the current `tests/integration/test_metalearth_scoring_api.py` coverage so it exercises the HTTP API, not only direct Python service calls.

Recommended direction:

- create a test app / client fixture that uses the normal FastAPI routes with a test database
- create workspace/profile/settings through API endpoints
- create or seed content items through supported test helpers
- invoke scoring through the pipeline/service layer only after workspace settings have been written through the API path
- verify results via API responses

2. Ensure the API tests specifically catch the bug class found in review:

- client writes camelCase threshold keys
- persisted settings are normalized
- scorer consumes them correctly
- content detail/list API reflects the expected score behavior

3. Keep synthetic data deterministic. Do not depend on network feeds here.

## Files to modify

- `tests/integration/conftest.py`
- `tests/integration/test_metalearth_scoring_api.py`
- optionally split into:
  - `tests/integration/test_metalearth_scoring_http_api.py`
  - `tests/integration/test_metalearth_diagnostics_api.py`

## Required tests

Required integration cases:

1. `test_api_settings_write_with_camelcase_affects_scoring_runtime`
2. `test_api_trusted_domains_write_affects_source_authority_runtime`
3. `test_content_detail_api_exposes_theme_competitor_filter_diagnostics`
4. `test_nonzero_threshold_excludes_weak_items_in_standard_metalearth_flow`
5. `test_strong_metalearth_article_outranks_generic_noise_via_api_observation`

## Pass 3 acceptance criteria

- integration tests hit the real FastAPI contract
- the key-normalization bug class is covered by tests
- the tests are deterministic and runnable locally

---

# Pass 4 — Repair the integration test harness so it is runnable in CI/local environments

## Goal

Make the new integration suite a reliable gate instead of a setup failure.

## Required work

1. Fix `tests/integration/conftest.py` so it does not fail during app/settings import in the current test environment.

Possible directions:

- isolate the Redis/session monkeypatch from global app settings import side effects
- provide a test-safe env bootstrap before importing app modules
- relax only the test bootstrap path if needed, without weakening production validation

2. Ensure the new integration suite can run from the documented repo root/backend commands.

3. Confirm the feed-quality test module is in the correct layer.

If it only does offline source-file validation, either:

- keep it runnable under the integration suite with the fixed harness, or
- move it to a lighter-weight test layer that does not require app bootstrap

## Files to modify

- `tests/integration/conftest.py`
- `tests/integration/test_metalearth_feed_quality.py`
- optionally shared test bootstrap/helpers
- potentially `backend/app/config.py` only if a narrowly-scoped test bootstrap path is required

## Required tests

1. prove the integration suite boots without environment validation errors
2. keep feed-quality assertions runnable
3. ensure test commands work from documented locations

## Pass 4 acceptance criteria

- the new tests no longer fail during setup in a normal local test environment
- feed-quality tests and API integration tests both run successfully

---

# Pass 5 — Re-run and tighten Web UI / fixture coverage for the standard QA path

## Goal

Make the standard Metal Earth QA fixtures truthfully represent the runtime behavior after the settings-path fix.

## Required work

1. Re-check:

- `e2e/metalearth-real-flow.spec.ts`
- `tests/manual/opencode_full_flow_metalearth_real_feeds.py`

2. After Pass 1 is fixed, verify that:

- non-zero thresholds are actually applied in the standard QA path
- trusted domains are actually applied
- feed definitions still avoid the junk-heavy broad queries

3. Add targeted assertions where practical:

- the standard QA path is not debug mode
- the configured threshold is visible in the returned settings payload
- at least one top result reflects trusted-domain and/or thematic scoring behavior

4. Keep the UI copy truthful:

- deterministic scoring
- BM25 is lexical, not LLM scoring

## Files to modify

- `e2e/metalearth-real-flow.spec.ts`
- `tests/manual/opencode_full_flow_metalearth_real_feeds.py`
- optionally content-page/detail-page tests if more coverage is needed

## Required tests

1. one assertion that the saved settings payload reflects the intended threshold values
2. one assertion that the standard QA path is using the non-debug configuration
3. maintain the feed-quality anti-regression coverage

## Pass 5 acceptance criteria

- the real-flow fixtures reflect actual runtime behavior, not intended-only behavior
- UI/tests remain aligned with deterministic scoring truth

---

# Pass 6 — Run full automated verification with `make ci`

## Goal

Prove the repair is protected by the full automated suite before redeploy.

## Required work

Run:

```bash
make ci
```

If it fails:

- stop
- fix the underlying issue
- rerun until green

## Pass 6 acceptance criteria

- `make ci` passes with the new settings-path, diagnostics, and integration coverage in place

---

# Pass 7 — Redeploy with `make up`

## Goal

Validate the repaired implementation on the normal deployed stack.

## Required work

Run:

```bash
make up
```

Then confirm service health:

```bash
docker compose ps
```

If services fail:

- stop
- fix the root cause
- rerun `make up`

## Pass 7 acceptance criteria

- `make up` succeeds
- expected services are healthy
- no scoring/settings startup regressions are introduced

---

# Pass 8 — API QA on the deployed stack

## Goal

Verify the repaired settings path and diagnostics through the real deployed API.

## Required work

1. Create or reuse a Metal Earth QA workspace using the repaired standard QA flow.

2. Confirm via API that the workspace settings now reflect the intended scoring-related values.

Required checks:

- threshold keys visible in the expected API shape
- trusted-domain configuration present
- no ambiguity about debug vs standard QA mode

3. Trigger a real run and wait for completion.

4. Use the deployed API to verify:

- thresholding is actually active for the standard QA path
- strong items outrank weak items
- trusted domains materially affect source authority when applicable
- content detail exposes:
  - theme match metadata
  - competitor match metadata
  - filter reason
  - threshold information

5. Run the repaired diagnostic helper against the deployed workspace.

Suggested commands:

```bash
curl -sS http://localhost:8000/api/workspaces/<ws_id>/settings | python -m json.tool
curl -sS http://localhost:8000/api/workspaces/<ws_id>/content | python -m json.tool
curl -sS http://localhost:8000/api/content/<content_id> | python -m json.tool
python tests/manual/diagnostic_workspace_scores.py <ws_id>
```

## Pass 8 acceptance criteria

- deployed API confirms the repaired settings path is active
- trusted-domain boosts and non-zero thresholds are visible in runtime behavior
- the diagnostic helper runs successfully against the deployed API

---

# Pass 9 — Web UI QA on the deployed stack

## Goal

Confirm the operator experience now matches the intended repaired behavior.

## Required work

1. Open the Metal Earth workspace in the deployed app.

2. Verify the Content page:

- does not behave like silent debug mode
- does not present a wall of weak junk as the standard QA default
- sorts/highlights top results sensibly

3. Open representative content detail pages for:

- one strong franchise/licensing item
- one competitor item
- one weak/noisy item if present

Verify that the UI clearly shows:

- relevance
- BM25
- freshness
- source authority
- theme match details
- competitor match details
- filter reason / threshold info

4. Verify labels remain accurate:

- deterministic scoring
- no LLM implication for base content scoring

5. If Playwright coverage is practical, update it to assert these behaviors on the deployed stack.

## Pass 9 acceptance criteria

- the Web UI reflects the repaired settings/scoring behavior
- operators can understand why items scored high or low
- the standard QA flow no longer behaves like unintentional debug mode

---

## Final acceptance criteria

This follow-up work is complete only when all of the following are true:

1. Workspace threshold/trusted-domain settings are canonicalized and consumed consistently end-to-end.
2. The scorer behaves the same whether settings were submitted via camelCase API input or internal snake_case test data.
3. The intended standard Metal Earth QA threshold is actually active at runtime.
4. Trusted-domain boosts are actually active at runtime for the real QA path.
5. The deployed diagnostic helper works against the current public API contract.
6. Integration tests validate the real HTTP/API behavior, not just direct service calls.
7. The new test harness is runnable and no longer fails during setup in the current environment.
8. `make ci` passes.
9. `make up` succeeds.
10. Deployed-stack API QA passes.
11. Deployed-stack Web UI QA passes.

If any one of these is missing, the work is not complete.
