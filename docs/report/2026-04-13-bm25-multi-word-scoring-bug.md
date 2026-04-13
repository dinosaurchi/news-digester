# BM25 Multi-Word Token Mismatch — Scoring Bug Analysis

**Date:** 2026-04-13
**Severity:** HIGH
**Status:** OPEN
**Discovered during:** Pass 6 QA — Metal Earth manual E2E full-flow test
**Affected workspace:** `057d0e7b28f84f95998ef890d61f0b85` (Metal Earth QA 20260413-144553)
**Affected file:** `backend/app/services/scoring.py` — `compute_bm25_score()` (lines 284–297)

---

## Observation

The Content page for the Metal Earth QA workspace shows a maximum relevance score of only **27/100** across all content items, despite the workspace having a well-configured profile with relevant priority themes, 6 validated Google News RSS feeds, and 120 imported articles.

This is unexpectedly low and suggests either:
1. The feed sources return content that doesn't match the workspace profile (feed quality problem), or
2. The scoring algorithm has a bug that suppresses scores (scoring problem).

---

## Diagnosis

**This is a scoring algorithm bug, not a feed quality problem.**

### Root Cause

The `compute_bm25_score()` function at `scoring.py:284–297` performs token-level matching that is fundamentally incompatible with multi-word priority themes.

#### The Bug

```python
# Line 284: text is split into individual whitespace tokens
tokens = text.lower().split()
# Result: {"edge", "computing", "is", "transforming", "the", ...}

# Line 293-297: query term is looked up as a single multi-word key
term_lower = term.lower()        # e.g., "edge computing"
if term_lower in tf:              # NEVER TRUE! "edge computing" ≠ "edge"
    score += ...
```

The token frequency dict (`tf`) contains **individual words** as keys, but the query lookup uses the **full multi-word theme string**. A priority theme like `"Edge Computing"` becomes the lookup key `"edge computing"` which will never appear as a key in `tf` (which only has `"edge"`, `"computing"`, etc.).

#### Contrast with Other Scoring Components

| Function | Matching Strategy | Multi-Word Support |
|----------|------------------|-------------------|
| `compute_keyword_score()` (line 93) | Substring: `kw.lower() in lower_text` | ✅ Works |
| `compute_document_frequencies()` (line 247) | Substring: `term_lower in text.lower()` | ✅ Works |
| **`compute_bm25_score()` (line 297)** | **Exact key lookup: `term_lower in tf`** | **❌ BROKEN** |

Only BM25 scoring is broken. The other two functions that handle the same priority themes use substring matching and work correctly.

### Existing Tests Don't Catch This

All existing BM25 tests in `backend/app/tests/test_scoring.py` use **single-word query terms** (e.g., `"ai"`, `"cloud"`), which correctly match individual tokens. No test passes multi-word query terms like `"edge computing"` or `"generative ai"` and asserts a non-zero BM25 result.

| Test | Location | Gap |
|------|----------|-----|
| `TestBM25WithIDF` | `test_scoring.py:829` | Only single-word terms |
| `test_score_bounded_by_one` | `test_scoring.py:288` | Single-word term |
| `test_multiple_terms_accumulate` | `test_scoring.py:279` | Single-word terms |
| `TestMetalEarthRegression` | `test_scoring.py:1143` | Tests ranking order, not absolute score values |

---

## Numerical Impact Analysis

### Scoring Weights and Effective Contribution

The scoring system uses a weighted combination of 6 components. The default weights are:

| Component | Weight | Actual Contribution | Reason |
|-----------|--------|--------------------|--------|
| `keyword_score` | 0.25 | ~0.05 | Low ratio: only 1–2 of 9 themes match via substring (1/9 ≈ 0.11 → 0.11 × 0.25 = 0.028) |
| `competitor_mention_score` | 0.20 | ~0.00 | Most news articles don't mention Piececool, UGEARS, etc. |
| `freshness_score` | 0.20 | ~0.15 | Only reliably active component; decays linearly over 7 days |
| `source_authority_score` | 0.15 | ~0.05 | Modest for untrusted Google News domains |
| `bm25_score` | 0.20 | **0.00** | 🔴 **BUG: always zero for multi-word themes** |
| `content_type_prior_score` | 0.00 | 0.00 | Disabled by default (weight = 0.0) |
| **Total** | **1.00** | **~0.25** | **Displayed as 25** |

### Effective Weight Utilization

| Category | Components | Allocated Weight | Effective Weight |
|----------|-----------|-----------------|-----------------|
| **Dead weight** | BM25 (bug), competitor_mention (usually 0), content_type_prior (disabled) | **0.40 (40%)** | **0.00** |
| **Under-utilized** | keyword (low ratio) | **0.25 (25%)** | **~0.03–0.05** |
| **Active** | freshness, source_authority | **0.35 (35%)** | **~0.20** |

The system effectively operates with only **~25% of its scoring capacity**. A perfect article matching all priority themes would score ~27 instead of ~85+.

### Score Ceiling Calculation

For a hypothetical perfectly relevant article:

| Component | If Fixed | Current |
|-----------|----------|---------|
| keyword (1.0 match ratio) | 0.25 × 1.0 = **0.25** | 0.25 × 0.11 = **0.028** |
| competitor (mentioned) | 0.20 × 1.0 = **0.20** | 0.20 × 0.0 = **0.000** |
| freshness (today) | 0.20 × 1.0 = **0.20** | 0.20 × 0.75 = **0.150** |
| source_authority (trusted) | 0.15 × 1.0 = **0.15** | 0.15 × 0.30 = **0.045** |
| BM25 (all themes match) | 0.20 × 1.0 = **0.20** | 0.20 × 0.0 = **0.000** |
| **Total** | **1.00** | **0.223** |
| **Displayed as** | **100** | **22** |

---

## Workspace Profile Context

The Metal Earth QA workspace has 9 multi-word priority themes:

1. `"licensed merchandise and IP deals"`
2. `"Star Wars, Marvel, Disney franchise developments"`
3. `"toy industry trends and Toy Fair announcements"`
4. `"hobby retail channel and specialty store trends"`
5. `"3D model kit and metal puzzle market"`
6. `"new entertainment franchises with licensing potential"`
7. `"Hasbro, Mattel, and major toy company strategies"`
8. `"collectibles and gift product trends"`
9. `"aerospace and aviation milestones"`

**Every single theme is multi-word.** This means BM25 scoring produces exactly 0.0 for every content item in this workspace.

---

## Edge Cases

| Scenario | Expected Behavior | Actual Behavior |
|----------|------------------|-----------------|
| Single-word theme (e.g., `"AI"`) | BM25 matches `"ai"` token | ✅ Works correctly |
| Multi-word theme (e.g., `"Edge Computing"`) | BM25 matches `"edge"` and `"computing"` tokens | ❌ Returns 0.0 |
| Mixed themes (single + multi-word) | BM25 matches only single-word themes | ⚠️ Partial — works for 1-word, fails for multi-word |
| All multi-word themes | BM25 = 0 for all items | ❌ Entire BM25 weight wasted |
| Empty priority_themes | keyword=0, BM25=0, competitor=0 | ⚠️ Only freshness+authority contribute |

---

## Feed Quality Assessment

The feeds are **not the problem**. The 6 Google News RSS feeds returned 120 articles, covering:

- Metal Earth brand mentions (direct)
- Star Wars/Marvel toy licensing news
- Toy industry trends
- Competitor mentions (Piececool, UGEARS)
- Model kit hobby news
- Entertainment franchise licensing deals

The articles are relevant. The scoring algorithm just can't detect the relevance due to the BM25 bug.

---

## Recommended Fix

### Option A: Split multi-word query terms into tokens (recommended)

In `compute_bm25_score()`, split each query term into individual tokens before matching:

```python
# Before (broken):
term_lower = term.lower()
if term_lower in tf:
    score += idf.get(term_lower, 0) * (1 + tf[term_lower])

# After (fixed):
for token in term.lower().split():
    if token in tf:
        score += idf.get(token, 0) * (1 + tf[token])
```

This makes BM25 scoring consistent with how IDF is already computed (substring matching per term).

### Option B: Use substring matching (consistent with keyword_score)

Alternatively, count term frequency using substring matching:

```python
term_lower = term.lower()
tf_value = lower_text.count(term_lower)  # substring match
if tf_value > 0:
    score += idf.get(term_lower, 0) * (1 + tf_value)
```

### Option C: Enable content_type_prior by default

Separately, consider raising the `content_type_prior` weight from 0.0 to a small value (e.g., 0.05) to utilize this signal. This is independent of the BM25 fix.

---

## Test Coverage Gap

A regression test must be added that:

1. Passes multi-word query terms to `compute_bm25_score()`
2. Asserts the result is non-zero when matching text contains the theme words
3. Tests a workspace with all multi-word priority themes and verifies BM25 contributes to the combined score

---

## Impact Scope

- **All workspaces with multi-word priority themes** are affected
- **The seed workspaces** (`ws-1` through `ws-5`) likely have multi-word themes too
- **The demo workspace** (`ws-demo-001`) has multi-word themes like `"Generative AI"`, `"Hybrid Cloud Architecture"`, etc.
- **Only workspaces with exclusively single-word themes** (unlikely in practice) would be unaffected

This means the scoring quality improvement from Pass 4a is **significantly undermined** by this bug — the BM25 component (20% weight) has been contributing nothing for any real-world workspace.
