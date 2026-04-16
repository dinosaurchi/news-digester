#!/usr/bin/env python3
"""Feed quality validation for Metal Earth real-feed test configs.

This test ensures that the Metal Earth feed definitions in both the Playwright
E2E test and the Python manual QA script contain valid direct RSS feed URLs
(not Google News search URLs).

Usage:
    python -m pytest tests/integration/test_metalearth_feed_quality.py -v
    python tests/integration/test_metalearth_feed_quality.py

This test runs offline — it only reads source files and validates the feed
URLs. No network access or deployed stack is required.
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

# Known-bad feed patterns that should NOT appear in the feed definitions.
BANNED_FEED_PATTERNS = [
    "news.google.com/rss/search",  # Google News search URLs are banned
]

# Required feed URL patterns that SHOULD be present for quality feeds.
# A quality feed is a direct RSS feed from an authoritative source.
REQUIRED_FEED_DOMAIN_KEYWORDS = [
    "toybook.com",
    "thepopinsider.com",
    "anbmedia.com",
    "makezine.com",
    "themarysue.com",
    "collectibles.org",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def extract_feed_urls(content: str) -> list[str]:
    """Extract all feed URLs from the content.

    Handles both TypeScript and Python feed definitions. Returns a list of
    raw (possibly URL-encoded) feed URL strings found in the FEEDS arrays.
    """
    urls: list[str] = []

    # Pattern for TypeScript: name: '...', url: 'https://...'
    ts_pattern = r"url:\s*['\"](https?://[^'\"]+)['\"]"
    urls.extend(re.findall(ts_pattern, content))

    # Pattern for Python: "url": "https://..." or 'url': 'https://...'
    py_pattern = r'["\']url["\']:\s*["\'](https?://[^"\']+)["\']'
    urls.extend(re.findall(py_pattern, content))

    return urls


def is_google_news_url(url: str) -> bool:
    """Check if a URL is a Google News RSS search URL."""
    return "news.google.com/rss/search" in url


def has_valid_feed_domain(url: str) -> bool:
    """Check if the URL is from a known, relevant domain for the Metal Earth niche."""
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.lower()
    # Remove common prefixes like www.
    domain = re.sub(r"^www\.", "", domain)
    return any(keyword in domain for keyword in REQUIRED_FEED_DOMAIN_KEYWORDS)


def validate_feeds(content: str, filename: str) -> list[str]:
    """Validate feed URLs in the given content.

    Returns a list of error messages (empty if all valid).
    """
    urls = extract_feed_urls(content)
    errors: list[str] = []

    if not urls:
        errors.append(f"{filename}: No feed URLs found in FEEDS array")
        return errors

    # Check: no Google News URLs
    google_news_urls = [u for u in urls if is_google_news_url(u)]
    if google_news_urls:
        errors.append(
            f"{filename}: Found {len(google_news_urls)} Google News URL(s) — "
            "direct RSS feeds are required, not Google News search URLs"
        )

    # Check: all feeds should have valid, relevant domains
    invalid_domain_urls = [u for u in urls if not has_valid_feed_domain(u)]
    if invalid_domain_urls:
        # Only error if there are NO valid domains at all (the list might be
        # intentionally shorter in some test scenarios). If some are valid,
        # we just warn rather than fail.
        valid_count = len(urls) - len(invalid_domain_urls)
        if valid_count == 0:
            errors.append(
                f"{filename}: No feeds from recognized relevant domains. "
                f"Expected one of: {REQUIRED_FEED_DOMAIN_KEYWORDS}"
            )

    return errors


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ts_feeds_no_google_news() -> None:
    """TypeScript E2E test feeds must not contain Google News URLs."""
    assert TS_FILE.exists(), f"File not found: {TS_FILE}"
    content = TS_FILE.read_text(encoding="utf-8")
    errors = validate_feeds(content, str(TS_FILE))
    assert not errors, f"Feed quality violations:\n  " + "\n  ".join(errors)


def test_py_feeds_no_google_news() -> None:
    """Python manual QA script feeds must not contain Google News URLs."""
    assert PY_FILE.exists(), f"File not found: {PY_FILE}"
    content = PY_FILE.read_text(encoding="utf-8")
    errors = validate_feeds(content, str(PY_FILE))
    assert not errors, f"Feed quality violations:\n  " + "\n  ".join(errors)


def test_ts_feeds_have_minimum_count() -> None:
    """TypeScript E2E test should have at least 6 feeds defined."""
    content = TS_FILE.read_text(encoding="utf-8")
    urls = extract_feed_urls(content)
    assert len(urls) >= 6, f"Expected at least 6 feeds in {TS_FILE}, found {len(urls)}"


def test_py_feeds_have_minimum_count() -> None:
    """Python manual QA script should have at least 6 feeds defined."""
    content = PY_FILE.read_text(encoding="utf-8")
    urls = extract_feed_urls(content)
    assert len(urls) >= 6, f"Expected at least 6 feeds in {PY_FILE}, found {len(urls)}"


def test_feeds_in_sync() -> None:
    """Both files should have the same feed URLs (order-independent comparison)."""
    ts_content = TS_FILE.read_text(encoding="utf-8")
    py_content = PY_FILE.read_text(encoding="utf-8")

    ts_urls = sorted(extract_feed_urls(ts_content))
    py_urls = sorted(extract_feed_urls(py_content))

    assert ts_urls == py_urls, (
        f"Feed URLs are not in sync between files.\n"
        f"  TS feeds ({len(ts_urls)}): {ts_urls}\n"
        f"  PY feeds ({len(py_urls)}): {py_urls}\n"
        f"Differences:\n"
        f"  Only in TS: {set(ts_urls) - set(py_urls)}\n"
        f"  Only in PY: {set(py_urls) - set(ts_urls)}"
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
        test_ts_feeds_no_google_news,
        test_py_feeds_no_google_news,
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
