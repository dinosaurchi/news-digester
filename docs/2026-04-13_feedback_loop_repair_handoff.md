# Feedback Loop Repair — Multi-Pass Handoff

## Goal

Fix the broken feedback-to-scoring pipeline so that user feedback **actually influences** future content scoring, report generation, and system behaviour — not just stored for display.

This handoff is a **focused repair pass** on the existing feedback infrastructure. The tables, endpoints, and UI already exist; the wiring between them is broken or missing.

---

## Current issues observed (with evidence)

### Issue 1 — Feedback events never flow to scoring (broken pipeline)

**Location:** `POST /api/workspaces/{id}/feedback` → `feedback_service.create_feedback_event()` → `feedback_events` table (dead end)

The scoring pipeline (`scoring.py:_load_feedback_signals`) reads **only** from `topic_preferences` and `source_preferences` tables. When a user submits a `topic_preference` or `source_preference` feedback event via the API, it creates a `FeedbackEvent` row but **never** creates or updates a `TopicPreference` or `SourcePreference` record.

Only the separate `PUT /workspaces/{id}/preferences/topics` endpoint populates the preference tables that scoring actually reads.

**Evidence:** In the deployed database, workspace `ws-1` has 12 feedback events including `topic_preference` events for "Generative AI" and "Cybersecurity Regulations", but zero topic preference adjustments were ever applied from those events — only from preferences that were inserted directly into the preference tables.

**Impact:** The primary feedback-to-scoring connection is severed. Users can submit feedback all day and it will never affect what content gets scored higher or lower.

### Issue 2 — Thumbs up/down votes have zero effect

**Location:** `reports.py:187-218` (thumb_message endpoint)

Message votes create `FeedbackEvent` records and update `report_messages.feedback`, but nothing ever reads these signals to adjust future scoring, shortlisting, or report generation. They are purely cosmetic.

**Evidence:** 1 message has a `feedback` value in the database. Zero of the 935 scored content items in `ws-1` show any thumbs-derived adjustment.

**Impact:** Users vote on report quality but the system never learns from it.

### Issue 3 — Topic matching produces zero results (too rigid)

**Location:** `scoring.py:636-637`

```python
if topic_key in lower_text:
```

Topic preferences use exact full-phrase substring matching. With multi-word topics like "Generative AI", "Cybersecurity Regulations", "Edge Computing", an article must contain the **exact phrase** to match.

**Evidence:** In `ws-1` (935 scored items, 3 topic preferences), **zero** items had a topic preference match. The article "DataNexus Launches AI-Powered Analytics Platform" does not match "Generative AI" because the exact substring doesn't appear.

**Impact:** Even when topic preferences exist and are correctly stored, they have no practical effect on scoring because the matching is too strict.

### Issue 4 — `build_score_breakdown()` strips feedback data from API

**Location:** `content.py:61-84`

The content detail API endpoint calls `build_score_breakdown()` which returns only 4 fields (`relevance`, `llm`, `freshness`, `sourceAuthority`). The `feedback_adjustment`, `topics_matched`, `sources_matched`, `feedback` data stored in `score_breakdown_json` is silently dropped.

**Evidence:** `GET /api/content/{id}` returns `{"relevance": 0.0, "llm": 0.0, "freshness": 0.9901, "sourceAuthority": 0.5}` but the raw DB record for the same item contains `feedback_adjustment: 0.1` and `sources_matched: ["techcrunch"]`.

**Impact:** The frontend has no visibility into whether feedback actually affected a content item's score. This makes it impossible for users to understand or debug feedback influence.

### Issue 5 — Vote toggle creates misleading feedback events

**Location:** `reports.py:202-213`

When a user clicks the same vote to toggle it off, the endpoint still creates a new `FeedbackEvent` with the original `feedback_type` (`thumbs_up` or `thumbs_down`) but `sentiment: "neutral"`. This inflates the event count and makes the feedback event timeline misleading — a toggle-off looks like a new feedback action.

**Evidence:** The code unconditionally creates a `FeedbackEvent` on every thumb click, regardless of whether the net action was "add vote", "change vote", or "remove vote".

**Impact:** Feedback event counts and summaries are unreliable. A user who clicks thumbs-up then clicks it again to remove it generates 2 events (one positive, one neutral) instead of 0 net events.

### Issue 6 — Feedback summary mislabels sentiments

**Location:** `feedback.py:49`

```python
"sentiment": "positive" if tp.weight >= 1.0 else "neutral",
```

- Weight 1.0 (neutral/default) → labeled "positive"
- Weight -1.0 (suppress) → labeled "neutral" instead of "negative"

**Impact:** The feedback summary dashboard shows incorrect sentiment labels. A suppression preference (negative weight) appears as "neutral" and a neutral preference (weight 1.0) appears as "positive".

### Issue 7 — BM25 scoring drops multi-word priority themes

**Location:** `scoring.py:261-300` (`compute_bm25_score()`)

`compute_document_frequencies()` computes IDF values for full query strings using substring checks, but `compute_bm25_score()` tokenises the document text into single-word tokens and then looks up each **entire query term** as a single key in the token-frequency map.

For a priority theme like `"edge computing"`:
- IDF is computed for the full string `"edge computing"`
- TF keys are `"edge"` and `"computing"`
- The lookup `if "edge computing" in tf` is always false

This means BM25 contributes `0.0` for multi-word priority themes even when all component words are present in the content.

**Evidence:** Direct reproduction against the current helper returns `0.0` for text containing both words of `"edge computing"` and `"cloud security"` when those themes are passed as query terms in a multi-document batch.

**Impact:** Workspaces that rely on realistic multi-word priority themes lose the BM25 component entirely or partially, wasting a configured relevance weight and depressing final scores for otherwise relevant content.

---

## Non-negotiable requirements

- Feedback events of type `topic_preference` and `source_preference` must create/update actual preference records that scoring reads
- Thumbs up/down must have a measurable downstream effect (at minimum, tracked and surfaced; ideally influencing future scoring)
- Topic matching must be flexible enough to produce non-zero matches on realistic data
- BM25 scoring must handle multi-word priority themes correctly
- `build_score_breakdown()` must expose feedback adjustment data to the API
- Vote toggle must not create misleading feedback events
- Sentiment labels must be correct
- All existing tests must continue to pass — do not break working functionality
- `make ci` must pass after each pass
- Each pass must include unit tests that prove the specific issue is fixed
- Dedicated QA passes must deploy with `make up` and validate via both API (curl/integration) and Web UI (Playwright E2E)

---

## Scope boundaries

**In scope:**
- Backend feedback event → preference conversion
- Backend topic matching improvement
- Backend BM25 multi-word theme matching repair
- Backend score breakdown API enrichment
- Backend vote event semantics
- Backend sentiment label fix
- Frontend feedback visibility improvements (if score breakdown data is newly exposed)
- Unit tests for all fixes
- Playwright E2E tests for feedback flows
- Integration tests for feedback-to-scoring pipeline
- Deployment and QA validation

**Out of scope:**
- ML-based feedback learning loops
- Embedding/vector-based topic matching
- Per-user feedback tracking (stays workspace-scoped)
- Report style preferences (UI exists but logic is not present — future work)
- Feedback-informed LLM prompt injection into report generation

---

## Implementation passes

Follow these passes in order.
Do not skip ahead if the earlier pass is unstable.
`make ci` must pass at the end of every pass before proceeding to the next.

---

# Pass 1 — Feedback event → preference conversion

## Goal

When a user submits a `topic_preference` or `source_preference` feedback event, the system must create or update the corresponding `TopicPreference` or `SourcePreference` record so that scoring actually reads it.

## Problems to fix

- `POST /api/workspaces/{id}/feedback` with `type: "topic_preference"` creates a `FeedbackEvent` but never touches the `topic_preferences` table
- `POST /api/workspaces/{id}/feedback` with `type: "source_preference"` creates a `FeedbackEvent` but never touches the `source_preferences` table
- The feedback summary fallback path (lines 54-69 in `feedback.py`) aggregates from events when no preferences exist, but this fallback data also never feeds into scoring

## Implementation tasks

### 1.1 Add preference upsert logic on feedback event creation

In `feedback_service.create_feedback_event()` (or in the API endpoint `feedback.py:57-94`), after creating the `FeedbackEvent`:

- If `feedback_type == "topic_preference"` and `value` is non-empty:
  - Upsert a `TopicPreference` for this workspace with `topic=value`
  - Set `weight` based on `sentiment`:
    - `"positive"` → weight +1.0 (or increment existing weight by +1.0)
    - `"negative"` → weight -1.0 (or decrement existing weight by -1.0)
    - `"neutral"` or missing → weight 0.0 (or reset)
  - Use upsert semantics: if a preference for this topic already exists, update the weight and `updated_at`; do not delete-and-recreate (preserve history/decay)

- If `feedback_type == "source_preference"` and `value` is non-empty:
  - Same logic for `SourcePreference` with `source_name=value`

### 1.2 Decide on weight accumulation vs replacement

Design decision required:
- **Option A (accumulative):** Each feedback event adds/subtracts from the existing weight. Repeated positive feedback for "AI" increases its weight over time.
- **Option B (replacement):** Each feedback event sets the weight to a fixed value based on sentiment. Latest event wins.

Recommendation: **Option A** (accumulative) with a reasonable cap (e.g., ±5.0). This makes repeated feedback meaningful.

### 1.3 Handle entity preferences similarly (if applicable)

If `entity_preference` feedback events exist or are planned, apply the same pattern.

## Files to modify

- `backend/app/services/feedback.py` — add preference upsert logic
- `backend/app/api/feedback.py` — possibly, if the conversion logic lives at the API layer

## Unit tests (new file: `backend/app/tests/test_feedback_preference_conversion.py`)

### Required test cases:

1. **`test_topic_preference_event_creates_preference_record`**
   - Create workspace
   - POST feedback event with `type: "topic_preference"`, `value: "AI"`, `sentiment: "positive"`
   - Query `TopicPreference` table
   - Assert: a `TopicPreference` exists for this workspace with `topic="AI"` and `weight > 0`

2. **`test_source_preference_event_creates_preference_record`**
   - Same pattern for `type: "source_preference"`, `value: "TechCrunch"`
   - Assert: a `SourcePreference` exists with `source_name="TechCrunch"` and `weight > 0`

3. **`test_negative_topic_preference_creates_negative_weight`**
   - POST feedback with `sentiment: "negative"` for a topic
   - Assert: `TopicPreference.weight < 0`

4. **`test_repeated_positive_feedback_accumulates_weight`**
   - POST 3 positive topic_preference events for the same topic
   - Assert: weight is higher than after 1 event (if using accumulative mode)

5. **`test_preference_updated_at_refreshed_on_new_event`**
   - Create a preference, wait briefly, create another event for the same topic
   - Assert: `updated_at` is more recent than `created_at`

6. **`test_feedback_event_still_created_alongside_preference`**
   - POST a topic_preference feedback event
   - Assert: both `FeedbackEvent` row AND `TopicPreference` row exist

7. **`test_existing_put_preferences_endpoint_still_works`**
   - `PUT /preferences/topics` with explicit preferences
   - Assert: preferences are set correctly (no regression)

8. **`test_feedback_preference_isolated_by_workspace`**
   - Create feedback events in workspace A
   - Assert: workspace B has no preferences

## Acceptance criteria

- [ ] A `topic_preference` feedback event creates/updates a `TopicPreference` record
- [ ] A `source_preference` feedback event creates/updates a `SourcePreference` record
- [ ] The scoring pipeline sees the new preferences on the next scoring run (no code change needed in scoring — it already reads from preference tables)
- [ ] Existing `PUT /preferences/topics` and `PUT /preferences/sources` endpoints still work correctly
- [ ] All new tests pass
- [ ] All existing tests pass
- [ ] `make ci` passes

---

# Pass 2 — Topic matching improvement

## Goal

Make topic preference matching flexible enough to produce non-zero results on realistic content.

## Problem to fix

The current matching (`scoring.py:636-637`) uses exact full-phrase substring matching. A topic preference for "Generative AI" only matches text containing that exact substring. Articles about "AI", "artificial intelligence", "GenAI", "generative artificial intelligence", or "AI-Powered" do not match.

## Implementation tasks

### 2.1 Implement word-level matching

Replace the exact-phrase check with word-level matching: split the topic into individual words and check if **all** words appear in the text (AND logic) or if **any** word appears (OR logic).

Recommendation: **All words must appear** (AND logic), but each word is matched independently. This is more flexible than exact-phrase matching but still precise enough to avoid false positives.

Example:
- Topic: "Generative AI"
- Words: ["generative", "ai"]
- Text: "AI-Powered generative model" → ✅ match (both "generative" and "ai" appear)
- Text: "AI breakthrough" → ❌ no match ("generative" not found)
- Text: "Generative art trends" → ❌ no match ("ai" not found)

### 2.2 Handle single-word topics

Single-word topics like "AI" should use word-boundary matching to avoid matching "MAIL" or "PAIR". Use `\bai\b` regex or split-and-check on word tokens.

### 2.3 Update `_compute_feedback_adjustment()` in `scoring.py`

Replace the line:
```python
if topic_key in lower_text:
```

With the new matching logic. Keep it deterministic and efficient — no ML or embeddings.

## Files to modify

- `backend/app/services/scoring.py` — `_compute_feedback_adjustment()` function (lines 635-654)

## Unit tests (add to `backend/app/tests/test_feedback_hooks.py` or new file)

### Required test cases:

1. **`test_multiword_topic_matches_when_all_words_present`**
   - Topic: "Generative AI", Text: "New generative models using AI"
   - Assert: adjustment > 0, topic matched

2. **`test_multiword_topic_no_match_when_partial_words`**
   - Topic: "Generative AI", Text: "New AI model released"
   - Assert: no topic match (only "AI" present, "generative" missing)

3. **`test_single_word_topic_matches_with_boundary`**
   - Topic: "AI", Text: "AI is transforming industries"
   - Assert: topic matched

4. **`test_single_word_topic_no_false_positive`**
   - Topic: "AI", Text: "The email said MAIN and PAIR"
   - Assert: no match (no standalone "ai" word)

5. **`test_case_insensitive_matching`**
   - Topic: "edge computing", Text: "EDGE COMPUTING trends"
   - Assert: match

6. **`test_topic_matching_with_realistic_data`**
   - Use real-world-like items: "Enterprise AI Adoption Reaches 40% Quarter-over-Quarter Growth"
   - Topic: "Generative AI"
   - Assert: no match (article is about "Enterprise AI", not "Generative AI")

7. **`test_topic_matching_regression_exact_phrase_still_works`**
   - Topic: "cybersecurity", Text: "New cybersecurity regulations proposed"
   - Assert: still matches (backward compatible)

## Acceptance criteria

- [ ] Multi-word topics match when all words are present in any order
- [ ] Single-word topics use word-boundary matching to avoid false positives
- [ ] Matching is case-insensitive
- [ ] Realistic content items (from Metal Earth / TechCorp-like data) produce non-zero topic matches when relevant preferences exist
- [ ] No false positives from substring partial matches
- [ ] All existing scoring tests still pass
- [ ] `make ci` passes

### 2.4 Repair BM25 matching for multi-word priority themes

The current BM25 helper is inconsistent with its own query term and IDF handling:
- `compute_document_frequencies()` treats each query term as a full phrase for IDF
- `compute_bm25_score()` only matches exact single-token keys in `tf`

This must be fixed so multi-word priority themes contribute to BM25 instead of always returning zero.

Recommendation:
- Normalise query terms into word tokens
- Score each query term by aggregating the matched token frequencies for its component words
- Preserve the existing score cap and normalisation behaviour so this remains a lightweight BM25-style signal, not a scoring rewrite

Example expected behaviour:
- Query term: `"edge computing"`
- Text: `"Enterprise edge platforms are reshaping computing infrastructure"`
- Result: BM25 contribution is non-zero because both `"edge"` and `"computing"` appear

Guardrails:
- Single-word query terms must keep their current behaviour
- Multi-word terms should not require the exact phrase order
- Matching should be case-insensitive
- Punctuation boundaries should not prevent obvious matches

### 2.5 Update `compute_bm25_score()` and related regression coverage

Files to modify:
- `backend/app/services/scoring.py` — `compute_bm25_score()` and any helper logic needed for consistent token matching
- `backend/app/tests/test_scoring.py` — add multi-word BM25 regressions

Required unit tests:

1. **`test_bm25_multiword_term_matches_when_component_words_present`**
   - Text contains both words from `"edge computing"`
   - Assert: BM25 score is greater than 0

2. **`test_bm25_multiword_term_no_match_when_only_partial_words_present`**
   - Text contains `"edge"` but not `"computing"`
   - Assert: BM25 contribution is 0

3. **`test_bm25_mixed_single_and_multiword_terms`**
   - Query terms include `"ai"` and `"cloud security"`
   - Assert: both term types can contribute in the same score

4. **`test_bm25_multiword_matching_case_insensitive`**
   - Query term `"edge computing"`, text `"EDGE COMPUTING trends"`
   - Assert: score is greater than 0

5. **`test_bm25_multiword_regression_with_batch_idf`**
   - Compute IDF across multiple documents for `"edge computing"`
   - Assert: a matching document gets non-zero BM25 with the computed IDF map

6. **`test_score_content_items_multiword_priority_themes_contribute_bm25`**
   - Workspace uses realistic multi-word priority themes
   - Score at least one matching item
   - Assert: `score_breakdown_json["scores"]["bm25"] > 0`

Add acceptance criteria for this BM25 repair:

- [ ] Multi-word priority themes contribute non-zero BM25 when their component words appear in content
- [ ] Partial-word or partial-theme matches do not incorrectly inflate BM25
- [ ] Existing single-word BM25 behaviour remains covered
- [ ] `score_content_items()` shows non-zero BM25 for realistic multi-word workspace themes
- [ ] All existing scoring tests still pass
- [ ] `make ci` passes

---

# Pass 3 — Score breakdown API enrichment & sentiment label fix

## Goal

Expose feedback adjustment data through the content detail API so the frontend can display it. Fix sentiment label logic.

## Problems to fix

1. `build_score_breakdown()` (`content.py:61-84`) strips all feedback data from the API response
2. Sentiment labels in `get_feedback_summary()` (`feedback.py:49`) misclassify weights

## Implementation tasks

### 3.1 Enrich `build_score_breakdown()` return value

Add feedback-related fields to the returned dict when they exist in `score_breakdown_json`:

```python
# After the existing 4 fields:
if breakdown.get("feedback_adjustment") is not None:
    result["feedbackAdjustment"] = round(float(breakdown["feedback_adjustment"]), 4)
if "feedback" in breakdown:
    fb = breakdown["feedback"]
    result["feedback"] = {
        "topicsMatched": fb.get("topics_matched", []),
        "sourcesMatched": fb.get("sources_matched", []),
        "eventCount": fb.get("event_count", 0),
    }
```

### 3.2 Fix sentiment labels in feedback summary

In `feedback.py:49`, change:
```python
"sentiment": "positive" if tp.weight >= 1.0 else "neutral",
```
To:
```python
"sentiment": "positive" if tp.weight > 0 else ("negative" if tp.weight < 0 else "neutral"),
```

Apply the same fix for source preferences at line ~80.

### 3.3 Fix vote toggle event creation

In `reports.py:202-213`, when `new_feedback is None` (toggle-off), either:
- **Option A:** Do not create a `FeedbackEvent` at all (toggle-off is not a feedback action)
- **Option B:** Create a `FeedbackEvent` with `feedback_type: "vote_removed"` to distinguish it from real votes

Recommendation: **Option A** — a toggle-off is the absence of feedback, not new feedback.

## Files to modify

- `backend/app/services/content.py` — `build_score_breakdown()`
- `backend/app/services/feedback.py` — `get_feedback_summary()` sentiment logic
- `backend/app/api/reports.py` — `thumb_message()` toggle logic

## Unit tests

### Required test cases:

1. **`test_score_breakdown_includes_feedback_adjustment`**
   - Score an item with a source preference that matches
   - Call `build_score_breakdown(item)`
   - Assert: `"feedbackAdjustment"` key exists with correct value

2. **`test_score_breakdown_includes_feedback_details`**
   - Assert: `"feedback"` key with `topicsMatched`, `sourcesMatched`, `eventCount`

3. **`test_score_breakdown_no_feedback_when_none`**
   - Score an item with no matching preferences
   - Assert: `"feedbackAdjustment"` key absent (not zero — absent)

4. **`test_content_detail_api_returns_feedback_in_breakdown`**
   - Full API test: create workspace, set preferences, score items, GET `/api/content/{id}`
   - Assert: response `scoreBreakdown` contains `feedbackAdjustment`

5. **`test_sentiment_label_positive_weight`**
   - Weight 2.0 → sentiment "positive"

6. **`test_sentiment_label_negative_weight`**
   - Weight -1.0 → sentiment "negative"

7. **`test_sentiment_label_zero_weight`**
   - Weight 0.0 → sentiment "neutral"

8. **`test_sentiment_label_neutral_weight_one`**
   - Weight 1.0 → sentiment "positive" (this is a real preference, not neutral)

9. **`test_vote_toggle_off_no_event_created`**
   - Create message, vote thumbs up, vote thumbs up again (toggle off)
   - Assert: only 1 feedback event exists (the original vote), not 2

10. **`test_vote_change_creates_single_event`**
    - Vote thumbs up, then vote thumbs down
    - Assert: 2 events (one up, one down) — changing vote is real feedback

11. **`test_vote_toggle_off_clears_message_feedback`**
    - Toggle off a vote
    - Assert: `report_messages.feedback` is `None`

## Acceptance criteria

- [ ] `GET /api/content/{id}` returns `feedbackAdjustment` and `feedback` in `scoreBreakdown` when feedback affected the score
- [ ] Sentiment labels are correct: positive weight → "positive", negative → "negative", zero → "neutral"
- [ ] Vote toggle-off does not create misleading feedback events
- [ ] All existing tests pass
- [ ] `make ci` passes

---

# Pass 4 — Deploy and QA: API integration tests

## Goal

Deploy the fixes from Passes 1–3, including the BM25 repair in Pass 2, with `make up` and validate correctness via API-level integration tests.

## Prerequisite

- Passes 1–3 complete and all unit tests passing
- `make ci` passes

## Implementation tasks

### 4.1 Redeploy

```bash
make down && make up
```

Verify the app starts and migrates correctly.

### 4.2 API integration test script

Create `tests/integration/test_feedback_api.py` (or shell script) that runs against the live deployed stack at `http://localhost:3000` (or the configured base URL).

### API tests to implement:

1. **Feedback event → preference conversion (end-to-end)**
   - Create workspace via API
   - POST topic_preference feedback event: `{"type": "topic_preference", "value": "Renewable Energy", "sentiment": "positive"}`
   - GET `/preferences/topics`
   - Assert: "Renewable Energy" preference exists with positive weight

2. **Feedback preference affects scoring**
   - Create workspace with profile (priority_themes)
   - Add feed, ingest content (or seed content items)
   - POST source_preference feedback event for a source that exists in content
   - Trigger run-now
   - GET content items
   - Assert: items from the preferred source have `feedbackAdjustment > 0` in score breakdown

3. **Multi-word BM25 scoring verification**
   - Create workspace with multi-word priority themes such as `"edge computing"` and `"cloud security"`
   - Seed or ingest content where component words appear in relevant items
   - Trigger scoring
   - GET content items or content detail
   - Assert: relevant items show `scoreBreakdown.relevance > 0` and raw breakdown contains `bm25 > 0`

4. **Score breakdown API enrichment**
   - GET `/api/content/{id}` for an item that was scored with feedback
   - Assert: `scoreBreakdown` contains `feedbackAdjustment` and `feedback` keys

5. **Feedback summary sentiment correctness**
   - PUT topic preferences with mixed weights (positive, negative, zero)
   - GET `/feedback/summary`
   - Assert: sentiments correctly reflect weights

6. **Vote toggle correctness**
   - Create report, get message ID
   - POST thumb up
   - Assert: feedback event count = 1
   - POST thumb up again (toggle off)
   - Assert: feedback event count still = 1 (no new event)
   - Assert: message feedback = null

7. **Feedback events list enrichment**
   - Create several feedback events with thread/message references
   - GET `/feedback`
   - Assert: events include `reportTitle` and `messageExcerpt` where applicable

### 4.3 Run against deployed stack

Run the test script against the live stack and capture results.

## Files to create

- `tests/integration/test_feedback_api.py`

## Acceptance criteria

- [ ] `make up` succeeds with the updated code
- [ ] All 7 API integration tests pass against the deployed stack
- [ ] No regressions in existing API behaviour
- [ ] Feedback event → preference → scoring pipeline works end-to-end
- [ ] Multi-word priority themes produce non-zero BM25 in deployed scoring flows

---

# Pass 5 — Deploy and QA: Playwright E2E tests for Web UI

## Goal

Validate the feedback UI flows work correctly in the browser after deployment.

## Prerequisite

- Pass 4 complete
- Stack running via `make up`

## Implementation tasks

### 5.1 Create Playwright E2E test file

Create `e2e/feedback.spec.ts` following the patterns in the existing `e2e/full-ui.spec.ts`.

### E2E tests to implement:

1. **Feedback page loads with summary stats**
   - Navigate to `/workspaces/ws-1/feedback` (or the feedback page route)
   - Assert: page loads, summary stats visible (total events, thumbs up/down counts)

2. **Thumbs up/down on report message**
   - Navigate to a report thread page
   - Hover over an agent/system message
   - Click thumbs up
   - Assert: button shows active state (blue highlight)
   - Click thumbs up again (toggle off)
   - Assert: button returns to inactive state

3. **Thumbs up then thumbs down (change vote)**
   - Click thumbs up, then click thumbs down
   - Assert: thumbs down is active, thumbs up is inactive

4. **Feedback reflected in summary after voting**
   - Vote thumbs up on a message
   - Navigate to feedback page
   - Assert: thumbs up count increased by 1

5. **Content detail shows non-zero scoring for multi-word themed content**
   - Navigate to content page for a workspace with multi-word priority themes
   - Click a relevant content item
   - Assert: score breakdown section is visible and the item shows a materially non-zero relevance/final score

6. **Score breakdown shows feedback data (content detail)**
   - Navigate to content page for a workspace with preferences
   - Click on a content item
   - Assert: score breakdown section visible
   - If feedback adjustment exists, assert it is displayed

7. **Feedback page shows correct sentiment labels**
   - Navigate to feedback page for a workspace with topic/source preferences
   - Assert: positive-weight preferences show "positive" label
   - Assert: negative-weight preferences show "negative" label (not "neutral")

### 5.2 Test infrastructure

The Playwright config already exists at `playwright.config.ts` with:
- `baseURL: 'http://172.17.0.1:3000'`
- `testDir: './e2e'`
- Chromium browser

The login helper and workspace helper functions exist in `e2e/full-ui.spec.ts` — extract shared helpers into `e2e/helpers.ts` if needed, or duplicate the `login()` function.

## Files to create/modify

- `e2e/feedback.spec.ts` (new)
- `e2e/helpers.ts` (optional, for shared login/workspace helpers)

## Acceptance criteria

- [ ] All 7 Playwright E2E tests pass against the deployed stack
- [ ] Tests run via `npx playwright test e2e/feedback.spec.ts`
- [ ] No regressions in existing E2E tests (`npx playwright test e2e/full-ui.spec.ts`)
- [ ] Feedback UI correctly reflects the backend fixes from Passes 1–3

---

# Pass 6 — Final cleanup and regression verification

## Goal

Verify no regressions, clean up, and confirm everything works together.

## Implementation tasks

### 6.1 Run full test suite

```bash
make ci
```

All existing tests must pass.

### 6.2 Run all E2E tests

```bash
npx playwright test
```

All Playwright tests (existing + new) must pass.

### 6.3 Run backend tests

```bash
make backend-test
```

### 6.4 Manual smoke test (if needed)

- Create a fresh workspace
- Add feeds and trigger a run
- Verify that content matching multi-word priority themes receives non-zero BM25 in stored score breakdowns
- Submit topic/source preference feedback via the feedback page
- Trigger another run
- Verify scored content items reflect the preference (check score breakdown in content detail)
- Vote thumbs up on a report message
- Verify feedback summary shows the vote
- Toggle the vote off
- Verify feedback summary does not show a misleading extra event

### 6.5 Update docs if needed

- If any API response shapes changed, verify frontend TypeScript types are updated
- Ensure `FeedbackPage.tsx` and `ReportThreadPage.tsx` handle the new/changed data correctly

## Acceptance criteria

- [ ] `make ci` passes
- [ ] `npx playwright test` passes (all E2E tests)
- [ ] `make backend-test` passes
- [ ] No regressions in any existing functionality
- [ ] Manual smoke test passes (if performed)

---

## Overall acceptance criteria

All of the following must be true before the work is considered complete:

1. A `topic_preference` feedback event creates/updates a `TopicPreference` record that scoring reads
2. A `source_preference` feedback event creates/updates a `SourcePreference` record that scoring reads
3. Topic matching uses word-level matching instead of exact-phrase substring matching
4. Topic matching produces non-zero matches on realistic content data
5. `GET /api/content/{id}` returns `feedbackAdjustment` and `feedback` in `scoreBreakdown`
6. Sentiment labels in feedback summary are correct (positive/negative/neutral based on weight sign)
7. Vote toggle-off does not create misleading `FeedbackEvent` records
8. All new unit tests pass (≥20 new test cases across Passes 1–3)
9. All API integration tests pass against the deployed stack (Pass 4)
10. All Playwright E2E tests pass against the deployed stack (Pass 5)
11. All existing tests continue to pass — zero regressions
12. `make ci` passes after every pass
13. `make up` succeeds and the stack is operational

---

## Summary of files to modify

### Backend (modify existing):
- `backend/app/services/feedback.py` — add preference upsert on event creation; fix sentiment labels
- `backend/app/services/scoring.py` — improve topic matching in `_compute_feedback_adjustment()`
- `backend/app/services/content.py` — enrich `build_score_breakdown()` with feedback data
- `backend/app/api/reports.py` — fix vote toggle event creation

### Backend (new test files):
- `backend/app/tests/test_feedback_preference_conversion.py` — Pass 1 tests
- `backend/app/tests/test_topic_matching.py` — Pass 2 tests (or add to `test_feedback_hooks.py`)
- `backend/app/tests/test_score_breakdown_enrichment.py` — Pass 3 tests (or add to `test_feedback_hooks.py` / `test_content.py`)

### Integration tests (new):
- `tests/integration/test_feedback_api.py` — Pass 4 API integration tests

### E2E tests (new):
- `e2e/feedback.spec.ts` — Pass 5 Playwright E2E tests

### No migration needed
All required tables already exist. No schema changes are needed — only logic changes.

---

## Estimated effort per pass

| Pass | Scope | Relative Size |
|------|-------|---------------|
| 1 — Feedback event → preference conversion | Service logic + 8 unit tests | Small |
| 2 — Topic matching improvement | Scoring function + 7 unit tests | Small |
| 3 — Score breakdown API + sentiment + vote fix | 3 files + 11 unit tests | Small–Medium |
| 4 — Deploy + API integration tests | Deploy + 6 integration tests | Medium |
| 5 — Playwright E2E tests | 6 browser tests | Medium |
| 6 — Final cleanup and regression | Run full suites, smoke test | Small |

---

## Final instruction

Do not treat this as cosmetic cleanup.

These are **broken data pipelines** — feedback is collected and stored but never reaches the scoring system. The fixes must be verified at every layer: unit tests prove the logic, integration tests prove the API, E2E tests prove the UI.

Follow the passes in order. Do not skip ahead if the earlier pass is unstable. `make ci` must pass at the end of every pass.
