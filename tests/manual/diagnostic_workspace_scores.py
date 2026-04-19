#!/usr/bin/env python3
"""Diagnostic helper to analyze a workspace's content scores.

This script is intentionally NOT part of CI. It's a manual/analysis tool
that can be used to diagnose scoring issues in a deployed stack.

Usage:
    python tests/manual/diagnostic_workspace_scores.py <workspace_id>

Environment variables:
- ``SME_BASE_URL``: default ``http://127.0.0.1:8000/api``
- ``SME_USERNAME``: default ``admin``
- ``SME_PASSWORD``: default ``admin``
- ``SME_MAX_DETAIL_FETCHES``: max items to fetch detail for (default ``500``)

Output:
- Content count summary
- Per-source score distribution
- Component score distribution (relevance, bm25, freshness, sourceAuthority, feedbackAdjustment)
- Top unmatched themes (themes that never match any content)
- Top unmatched competitors (competitors that never appear in any content)
- Filter reasons / threshold behavior
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from http.cookiejar import CookieJar
from typing import Any


BASE_URL = os.environ.get("SME_BASE_URL", "http://127.0.0.1:8000/api").rstrip("/")
USERNAME = os.environ.get("SME_USERNAME", "admin")
PASSWORD = os.environ.get("SME_PASSWORD", "admin")
MAX_DETAIL_FETCHES = int(os.environ.get("SME_MAX_DETAIL_FETCHES", "500"))


class DiagnosticError(RuntimeError):
    """Raised when diagnostic analysis fails."""


class ApiClient:
    """Simple HTTP client for the SME API."""

    def __init__(self, base_url: str) -> None:
        self._jar = CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._jar)
        )
        self.base_url = base_url

    def login(self, username: str, password: str) -> None:
        """Authenticate and store session cookie."""
        payload = json.dumps({"username": username, "password": password}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/session/login",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            resp = self._opener.open(req)
            if resp.status != 200:
                raise DiagnosticError(f"Login failed: {resp.status}")
        except urllib.error.HTTPError as e:
            raise DiagnosticError(f"Login failed: {e.code} {e.reason}")

    def get(self, path: str) -> Any:
        """GET request returning JSON (list or dict)."""
        req = urllib.request.Request(f"{self.base_url}{path}")
        try:
            resp = self._opener.open(req)
            return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            raise DiagnosticError(f"GET {path} failed: {e.code} {e.reason} - {body}")


def _fetch_score_breakdowns(
    client: ApiClient, all_items: list[dict], max_fetches: int
) -> tuple[list[dict], int]:
    """Fetch scoreBreakdown for each item via the detail endpoint.

    Returns (breakdowns, items_without_breakdown).
    """
    breakdowns: list[dict] = []
    items_without_breakdown = 0
    detail_count = 0

    for item in all_items:
        if detail_count >= max_fetches:
            print(
                f"\n⚠ Stopped fetching details after {max_fetches} items "
                f"({len(all_items) - detail_count} remaining skipped)"
            )
            items_without_breakdown += len(all_items) - detail_count
            break

        try:
            detail = client.get(f"/content/{item['id']}")
            bd = detail.get("scoreBreakdown")
            if bd and isinstance(bd, dict):
                breakdowns.append(bd)
            else:
                items_without_breakdown += 1
        except DiagnosticError as e:
            print(f"\n⚠ Failed to fetch detail for {item['id']}: {e}")
            items_without_breakdown += 1
        detail_count += 1

    return breakdowns, items_without_breakdown


def analyze_workspace(client: ApiClient, workspace_id: str) -> None:
    """Analyze and report on a workspace's scoring metrics."""

    # Fetch workspace details
    workspace = client.get(f"/workspaces/{workspace_id}")
    print(f"\n{'=' * 70}")
    print(f"WORKSPACE DIAGNOSTIC: {workspace.get('name', 'Unknown')}")
    print(f"{'=' * 70}")

    # Fetch content items for this workspace (list endpoint returns plain list)
    all_items: list[dict] = client.get(f"/workspaces/{workspace_id}/content")

    if not all_items:
        print("\nNo content items found for this workspace.")
        return

    # Basic summary
    included = [i for i in all_items if i.get("status") == "included"]
    excluded = [i for i in all_items if i.get("status") == "excluded"]
    pending = [i for i in all_items if i.get("status") == "pending"]

    print(f"\n--- Content Summary ---")
    print(f"Total items: {len(all_items)}")
    print(f"Included:    {len(included)}")
    print(f"Excluded:    {len(excluded)}")
    print(f"Pending:     {len(pending)}")

    # Fetch score breakdowns from detail endpoint (N+1 pattern)
    print(f"\nFetching score breakdowns for up to {MAX_DETAIL_FETCHES} items...")
    breakdowns, items_without_breakdown = _fetch_score_breakdowns(
        client, all_items, MAX_DETAIL_FETCHES
    )

    if items_without_breakdown:
        print(f"⚠ Items without score breakdown: {items_without_breakdown}")

    if not breakdowns:
        print("\nNo scored items found. Run the scoring pipeline first.")
        return

    print(f"Score breakdowns retrieved: {len(breakdowns)}")

    # Score distribution — use combinedScore when available, fall back to relevance
    scores = [bd.get("combinedScore", bd.get("relevance", 0)) for bd in breakdowns]
    print(f"\n--- Score Distribution ---")
    if scores:
        print(f"Min score:  {min(scores):.4f}")
        print(f"Max score:  {max(scores):.4f}")
        print(f"Mean score: {statistics.mean(scores):.4f}")
        if len(scores) > 1:
            print(f"Median:     {statistics.median(scores):.4f}")
            print(f"Stdev:      {statistics.stdev(scores):.4f}")

    # Component score distribution (flattened camelCase keys from build_score_breakdown)
    component_keys = [
        "relevance",
        "bm25",
        "freshness",
        "sourceAuthority",
        "feedbackAdjustment",
    ]
    print(f"\n--- Component Score Distribution ---")
    print(f"{'Component':<22} {'Min':>8} {'Max':>8} {'Mean':>8} {'Non-zero':>10}")
    print("-" * 60)

    for key in component_keys:
        values = [bd.get(key, 0) for bd in breakdowns if bd.get(key) is not None]

        if values:
            non_zero = sum(1 for v in values if v > 0)
            print(
                f"{key:<22} {min(values):>8.3f} {max(values):>8.3f} "
                f"{statistics.mean(values):>8.3f} {non_zero:>8}/{len(values)}"
            )
        else:
            print(f"{key:<22} {'N/A':>8} {'N/A':>8} {'N/A':>8} {'N/A':>10}")

    # Per-source score distribution (camelCase "source" field from list endpoint)
    feed_scores: dict[str, list[float]] = defaultdict(list)
    for item, bd in zip(all_items, breakdowns):
        feed_name = item.get("source", "Unknown")
        score = bd.get("combinedScore", bd.get("relevance", 0))
        feed_scores[feed_name].append(score)

    print(f"\n--- Per-Source Score Distribution ---")
    print(f"{'Source':<40} {'Count':>6} {'Mean':>8} {'Min':>8} {'Max':>8}")
    print("-" * 74)

    for feed_name, feed_vals in sorted(feed_scores.items(), key=lambda x: -len(x[1])):
        if feed_vals:
            print(
                f"{feed_name[:39]:<40} {len(feed_vals):>6} "
                f"{statistics.mean(feed_vals):>8.3f} {min(feed_vals):>8.3f} {max(feed_vals):>8.3f}"
            )

    # Theme match analysis (camelCase "themeMatch" key from scoreBreakdown)
    theme_matched_counts: Counter = Counter()
    theme_unmatched_counts: Counter = Counter()
    themes_analyzed = 0

    for bd in breakdowns:
        theme_match = bd.get("themeMatch")
        if theme_match:
            themes_analyzed += 1
            for t in theme_match.get("matched", []):
                theme_matched_counts[t] += 1
            for t in theme_match.get("unmatched", []):
                theme_unmatched_counts[t] += 1

    if themes_analyzed:
        print(f"\n--- Theme Match Analysis (across {themes_analyzed} scored items) ---")

        # Top matched themes
        print("\nTop matched themes:")
        for theme, count in theme_matched_counts.most_common(10):
            print(f"  {theme:<30} matched in {count:>4} items")

        # Top unmatched themes (themes that rarely or never match)
        print("\nTop unmatched themes (potential candidates for removal/refinement):")
        for theme, count in theme_unmatched_counts.most_common(10):
            matched = theme_matched_counts.get(theme, 0)
            match_rate = matched / themes_analyzed * 100 if themes_analyzed else 0
            print(
                f"  {theme:<30} unmatched in {count:>4} items ({match_rate:.1f}% match rate)"
            )

    # Competitor match analysis (camelCase "competitorMatch" key from scoreBreakdown)
    comp_matched_counts: Counter = Counter()
    comp_unmatched_counts: Counter = Counter()
    comps_analyzed = 0

    for bd in breakdowns:
        comp_match = bd.get("competitorMatch")
        if comp_match:
            comps_analyzed += 1
            for c in comp_match.get("matched", []):
                comp_matched_counts[c] += 1
            for c in comp_match.get("unmatched", []):
                comp_unmatched_counts[c] += 1

    if comps_analyzed:
        print(
            f"\n--- Competitor Match Analysis (across {comps_analyzed} scored items) ---"
        )

        print("\nMatched competitors:")
        for comp, count in comp_matched_counts.most_common(10):
            print(f"  {comp:<30} mentioned in {count:>4} items")

        print("\nUnmatched competitors (never mentioned in content):")
        for comp, count in comp_unmatched_counts.most_common(10):
            matched = comp_matched_counts.get(comp, 0)
            if matched == 0:
                print(f"  {comp:<30} NEVER matched (unmatched in {count} items)")
            else:
                print(f"  {comp:<30} matched in {matched:>4} items ({count} unmatched)")

    # Exclusion analysis (camelCase "exclusionReason" field from list endpoint)
    exclusion_reasons: Counter = Counter()
    for item in all_items:
        reason = item.get("exclusionReason")
        if reason:
            exclusion_reasons[reason] += 1

    if exclusion_reasons:
        print(f"\n--- Exclusion Analysis ---")
        for reason, count in exclusion_reasons.most_common():
            print(f"  {reason:<35} {count:>4} items")

    # Filter reason analysis (from scoreBreakdown "filterReason" key)
    filter_reasons: Counter = Counter()
    filter_thresholds: list[float] = []
    for bd in breakdowns:
        fr = bd.get("filterReason")
        if fr:
            filter_reasons[fr] += 1
        thresh = bd.get("minRelevanceThreshold")
        if thresh is not None:
            filter_thresholds.append(thresh)

    if filter_reasons:
        print(f"\n--- Filter Reason Analysis (from scoreBreakdown) ---")
        for reason, count in filter_reasons.most_common():
            print(f"  {reason:<35} {count:>4} items")

    if filter_thresholds:
        unique_thresholds = sorted(set(filter_thresholds))
        print(f"\n--- Relevance Thresholds ---")
        for t in unique_thresholds:
            print(f"  {t:.4f}")

    print(f"\n{'=' * 70}")
    print("DIAGNOSTIC COMPLETE")
    print(f"{'=' * 70}\n")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python diagnostic_workspace_scores.py <workspace_id>")
        print(
            "       SME_BASE_URL=http://... SME_USERNAME=... SME_PASSWORD=... python diagnostic_workspace_scores.py <workspace_id>"
        )
        print(
            "       SME_MAX_DETAIL_FETCHES=1000 python diagnostic_workspace_scores.py <workspace_id>"
        )
        sys.exit(1)

    workspace_id = sys.argv[1]

    print(f"Connecting to {BASE_URL}...")
    client = ApiClient(BASE_URL)

    print(f"Logging in as {USERNAME}...")
    client.login(USERNAME, PASSWORD)
    print("Login successful.")

    analyze_workspace(client, workspace_id)


if __name__ == "__main__":
    main()
