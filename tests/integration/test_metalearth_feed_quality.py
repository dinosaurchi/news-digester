#!/usr/bin/env python3
"""Feed quality validation for Metal Earth real-feed test configs.

This test ensures that the Metal Earth feed definitions in both the Playwright
E2E test and the Python manual QA script do NOT contain known-bad broad query
tokens that produce junk articles (e.g., bare "Tenyo" pulls motorcycle death
articles, bare "licensing deal" pulls pharma deals).

Usage:
    python -m pytest tests/integration/test_metalearth_feed_quality.py -v
    python tests/integration/test_metalearth_feed_quality.py

This test runs offline — it only reads source files and validates the query
strings. No network access or deployed stack is required.
"""

from __future__ import annotations

import re
import sys
import urllib.parse
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration — paths to the files under validation
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
TS_FILE = REPO_ROOT / "e2e" / "metalearth-real-flow.spec.ts"
PY_FILE = REPO_ROOT / "tests" / "manual" / "opencode_full_flow_metalearth_real_feeds.py"

# Known-bad bare tokens that produce junk articles.
# These must NOT appear as standalone query terms (outside of quotes).
BANNED_BARE_TOKENS = [
    "Tenyo",  # Bare "Tenyo" pulls unrelated Japanese people/news
    "licensing deal",  # Bare "licensing deal" pulls pharma, tech, etc.
    "model kit brand",  # Bare "model kit brand" is too generic
]

# Allowed contextual usages — these are fine because they're in quoted phrases
# or combined with other terms to make them specific.
ALLOWED_PHRASES = [
    "Tenyo Metallic Nano",  # Exact competitor product line
    "toy licensing",  # Scoped to toy industry
    "consumer products licensing",
    "collectibles licensing",
    "franchise merchandise toys",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def extract_google_news_query_strings(content: str) -> list[str]:
    """Extract all query strings from Google News RSS URLs in the content.

    Handles both single-line URLs (TypeScript) and multi-line Python string
    concatenation patterns.

    Returns a list of decoded query strings (the ``q=`` parameter values).
    """
    queries: list[str] = []

    # Strategy 1: Single-line URLs (TypeScript style)
    url_pattern = r'https://news\.google\.com/rss/search\?[^"\s\']+'
    urls = re.findall(url_pattern, content)

    for url in urls:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        if "q" in params:
            queries.append(params["q"][0])

    # Strategy 2: Multi-line Python string concatenation
    # Pattern: "https://news.google.com/rss/search?" followed by one or more
    # continuation lines with "q=..." or "+..." fragments, ending with "),
    # We match the block between the opening URL and the closing ),
    multiline_blocks = re.findall(
        r'"https://news\.google\.com/rss/search\?"\s*\n'
        r'((?:\s*"[^"]*"\s*\n?)+)',
        content,
    )

    for block in multiline_blocks:
        # Extract all quoted string fragments
        fragments = re.findall(r'"([^"]*)"', block)
        # Reconstruct the full URL
        full_url = "https://news.google.com/rss/search?"
        for frag in fragments:
            full_url += frag

        # Parse the assembled URL
        if "q=" in full_url:
            try:
                parsed = urllib.parse.urlparse(full_url)
                params = urllib.parse.parse_qs(parsed.query)
                if "q" in params:
                    query = params["q"][0]
                    # Avoid duplicates with strategy 1
                    if query not in queries:
                        queries.append(query)
            except Exception:
                # If parsing fails, skip this block
                pass

    return queries


def url_decode_query(q: str) -> str:
    """Fully URL-decode a query string for analysis."""
    return urllib.parse.unquote_plus(q)


def contains_bare_token(query: str, token: str) -> bool:
    """Check if a query contains the token as a bare (unquoted) term.

    A token is "bare" if it appears outside of double-quoted phrases.
    This is a simplified check: we look for the token not wrapped in %22...".
    """
    decoded = url_decode_query(query)

    # Check if token appears in a quoted phrase (e.g., "Tenyo Metallic Nano")
    # If it's inside quotes, it's OK
    quoted_pattern = r"%22[^%]*" + re.escape(token.replace(" ", "+")) + r"[^%]*%22"
    if re.search(quoted_pattern, query, re.IGNORECASE):
        return False

    # Check if token appears outside quotes in decoded form
    # Split by quoted phrases and check remaining segments
    segments = re.split(r'"[^"]*"', decoded)
    for segment in segments:
        # Normalize whitespace for comparison
        normalized = re.sub(r"\s+", " ", segment.strip().lower())
        token_normalized = token.lower()
        if token_normalized in normalized:
            return True

    return False


def validate_feeds(content: str, filename: str) -> list[str]:
    """Validate feed queries in the given content.

    Returns a list of error messages (empty if all valid).
    """
    queries = extract_google_news_query_strings(content)
    errors: list[str] = []

    if not queries:
        errors.append(f"{filename}: No Google News RSS feed URLs found")
        return errors

    for i, query in enumerate(queries, 1):
        decoded = url_decode_query(query)
        for token in BANNED_BARE_TOKENS:
            if contains_bare_token(query, token):
                errors.append(
                    f"{filename}: Feed #{i} contains bare banned token "
                    f'"{token}" in query: {decoded}'
                )

    return errors


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ts_feeds_no_banned_tokens() -> None:
    """TypeScript E2E test feeds must not contain bare banned tokens."""
    assert TS_FILE.exists(), f"File not found: {TS_FILE}"
    content = TS_FILE.read_text(encoding="utf-8")
    errors = validate_feeds(content, str(TS_FILE))
    assert not errors, f"Feed quality violations:\n  " + "\n  ".join(errors)


def test_py_feeds_no_banned_tokens() -> None:
    """Python manual QA script feeds must not contain bare banned tokens."""
    assert PY_FILE.exists(), f"File not found: {PY_FILE}"
    content = PY_FILE.read_text(encoding="utf-8")
    errors = validate_feeds(content, str(PY_FILE))
    assert not errors, f"Feed quality violations:\n  " + "\n  ".join(errors)


def test_ts_feeds_have_minimum_count() -> None:
    """TypeScript E2E test should have at least 6 feeds defined."""
    content = TS_FILE.read_text(encoding="utf-8")
    queries = extract_google_news_query_strings(content)
    assert len(queries) >= 6, (
        f"Expected at least 6 feeds in {TS_FILE}, found {len(queries)}"
    )


def test_py_feeds_have_minimum_count() -> None:
    """Python manual QA script should have at least 6 feeds defined."""
    content = PY_FILE.read_text(encoding="utf-8")
    queries = extract_google_news_query_strings(content)
    assert len(queries) >= 6, (
        f"Expected at least 6 feeds in {PY_FILE}, found {len(queries)}"
    )


def test_feeds_in_sync() -> None:
    """Both files should have the same number of feeds with matching queries."""
    ts_content = TS_FILE.read_text(encoding="utf-8")
    py_content = PY_FILE.read_text(encoding="utf-8")

    ts_queries = [
        url_decode_query(q) for q in extract_google_news_query_strings(ts_content)
    ]
    py_queries = [
        url_decode_query(q) for q in extract_google_news_query_strings(py_content)
    ]

    # Sort for comparison (order shouldn't matter for sync check)
    ts_sorted = sorted(ts_queries)
    py_sorted = sorted(py_queries)

    assert ts_sorted == py_sorted, (
        f"Feed queries are not in sync between files.\n"
        f"  TS feeds ({len(ts_queries)}): {ts_sorted}\n"
        f"  PY feeds ({len(py_queries)}): {py_sorted}\n"
        f"Differences:\n"
        f"  Only in TS: {set(ts_sorted) - set(py_sorted)}\n"
        f"  Only in PY: {set(py_sorted) - set(ts_sorted)}"
    )


def test_ts_thresholds_are_standard_qa() -> None:
    """TypeScript E2E test should use 0.15 thresholds, not debug 0.0."""
    content = TS_FILE.read_text(encoding="utf-8")
    # Check for 0.0 thresholds (debug mode)
    assert "minRelevanceScore: 0.0" not in content, (
        f"{TS_FILE}: Still using debug threshold minRelevanceScore: 0.0"
    )
    assert "minFinalScore: 0.0" not in content, (
        f"{TS_FILE}: Still using debug threshold minFinalScore: 0.0"
    )
    # Check for 0.15 thresholds (standard QA)
    assert "minRelevanceScore: 0.15" in content, (
        f"{TS_FILE}: Missing standard QA threshold minRelevanceScore: 0.15"
    )
    assert "minFinalScore: 0.15" in content, (
        f"{TS_FILE}: Missing standard QA threshold minFinalScore: 0.15"
    )


def test_py_thresholds_are_standard_qa() -> None:
    """Python manual QA script should use 0.15 thresholds, not debug 0.0."""
    content = PY_FILE.read_text(encoding="utf-8")
    # Check for 0.0 thresholds (debug mode)
    assert '"minRelevanceScore": 0.0' not in content, (
        f"{PY_FILE}: Still using debug threshold minRelevanceScore: 0.0"
    )
    assert '"minFinalScore": 0.0' not in content, (
        f"{PY_FILE}: Still using debug threshold minFinalScore: 0.0"
    )
    # Check for 0.15 thresholds (standard QA)
    assert '"minRelevanceScore": 0.15' in content, (
        f"{PY_FILE}: Missing standard QA threshold minRelevanceScore: 0.15"
    )
    assert '"minFinalScore": 0.15' in content, (
        f"{PY_FILE}: Missing standard QA threshold minFinalScore: 0.15"
    )


# ---------------------------------------------------------------------------
# Main (for direct execution without pytest)
# ---------------------------------------------------------------------------


def main() -> int:
    """Run all tests and report results."""
    tests = [
        test_ts_feeds_no_banned_tokens,
        test_py_feeds_no_banned_tokens,
        test_ts_feeds_have_minimum_count,
        test_py_feeds_have_minimum_count,
        test_feeds_in_sync,
        test_ts_thresholds_are_standard_qa,
        test_py_thresholds_are_standard_qa,
    ]

    passed = 0
    failed = 0
    errors: list[str] = []

    for test_fn in tests:
        name = test_fn.__name__
        try:
            test_fn()
            print(f"  ✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {name}: {e}")
            failed += 1
            errors.append(f"{name}: {e}")
        except Exception as e:
            print(f"  ✗ {name}: UNEXPECTED: {e}")
            failed += 1
            errors.append(f"{name}: {e}")

    print(f"\nFeed quality validation: {passed} passed, {failed} failed")

    if errors:
        print("\nFailures:")
        for err in errors:
            print(f"  - {err}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
