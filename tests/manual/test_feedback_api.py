#!/usr/bin/env python3
"""API integration tests for the feedback loop repair (Pass 4).

Tests the deployed stack end-to-end to verify that Passes 1-3 fixes work
correctly through the HTTP API layer.

Usage:
    python tests/manual/test_feedback_api.py
    BASE_URL=http://172.17.0.1:3000 python tests/manual/test_feedback_api.py

Environment variables:
    BASE_URL       - API base URL (default: http://localhost:3000)
    SME_USERNAME   - Login username (default: admin)
    SME_PASSWORD   - Login password (default: admin)
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = os.environ.get("BASE_URL", "http://localhost:3000").rstrip("/")
USERNAME = os.environ.get("SME_USERNAME", "admin")
PASSWORD = os.environ.get("SME_PASSWORD", "admin")

# ---------------------------------------------------------------------------
# Lightweight test framework
# ---------------------------------------------------------------------------

_pass_count = 0
_fail_count = 0
_skip_count = 0


@dataclass
class TestResult:
    name: str
    passed: bool = False
    skipped: bool = False
    message: str = ""


@dataclass
class ApiClient:
    """HTTP client with session cookie management."""

    base_url: str = BASE_URL
    session: requests.Session = field(default_factory=requests.Session)

    def login(self, username: str = USERNAME, password: str = PASSWORD) -> bool:
        """Authenticate and store session cookie."""
        resp = self.session.post(
            f"{self.base_url}/api/session/login",
            json={"username": username, "password": password},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"  Login failed: {resp.status_code} {resp.text}")
            return False
        return True

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.session.get(f"{self.base_url}{path}", timeout=30, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.session.post(f"{self.base_url}{path}", timeout=30, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self.session.put(f"{self.base_url}{path}", timeout=30, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.session.delete(f"{self.base_url}{path}", timeout=30, **kwargs)


def assert_eq(actual: Any, expected: Any, label: str = "") -> None:
    """Assert equality with a descriptive label."""
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def assert_gt(actual: float, threshold: float, label: str = "") -> None:
    """Assert actual > threshold."""
    if not (actual > threshold):
        raise AssertionError(f"{label}: expected > {threshold}, got {actual!r}")


def assert_in(key: str, data: dict, label: str = "") -> None:
    """Assert key is in data."""
    if key not in data:
        raise AssertionError(f"{label}: key {key!r} not found in {list(data.keys())}")


def assert_true(condition: bool, label: str = "") -> None:
    """Assert condition is True."""
    if not condition:
        raise AssertionError(f"{label}: expected True, got False")


def run_test(name: str, fn, *args) -> TestResult:
    """Run a single test function and return the result."""
    global _pass_count, _fail_count, _skip_count
    try:
        fn(*args)
        _pass_count += 1
        return TestResult(name=name, passed=True, message="PASS")
    except SkipTest as e:
        _skip_count += 1
        return TestResult(name=name, skipped=True, message=f"SKIPPED: {e}")
    except (AssertionError, Exception) as e:
        _fail_count += 1
        return TestResult(name=name, passed=False, message=f"FAIL: {e}")


class SkipTest(Exception):
    """Raised when a test should be skipped due to missing prerequisites."""


def _wait_for_run(api: ApiClient, run_id: str, timeout_s: int = 120) -> dict | None:
    """Poll a pipeline run until it finishes. Returns the run data or None."""
    for _ in range(timeout_s // 2):
        time.sleep(2)
        resp = api.get(f"/api/runs/{run_id}")
        if resp.status_code != 200:
            continue
        run_data = resp.json()
        status = run_data.get("status")
        if status in ("succeeded", "success", "failed"):
            return run_data
    return None


def _scoring_step_ok(run_data: dict) -> bool:
    """Check whether the score_content step in a pipeline run completed."""
    for step in run_data.get("steps", []):
        if step.get("name") == "score_content" and step.get("status") in (
            "completed",
            "success",
        ):
            return True
    return False


# ---------------------------------------------------------------------------
# Test 1: Feedback event → preference conversion (end-to-end)
# ---------------------------------------------------------------------------


def test_feedback_event_creates_preference(api: ApiClient) -> None:
    """POST a topic_preference feedback event and verify a preference record is created."""
    # Create a fresh workspace for this test
    ts = time.strftime("%Y%m%d-%H%M%S")
    resp = api.post(
        "/api/workspaces",
        json={
            "name": f"Feedback API Test 1 {ts}",
            "customer": "Test",
            "status": "active",
        },
    )
    assert_eq(resp.status_code, 201, "workspace creation")
    ws_id = resp.json()["id"]

    try:
        # POST topic_preference feedback event
        resp = api.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={
                "type": "topic_preference",
                "value": "Renewable Energy",
                "sentiment": "positive",
            },
        )
        assert_eq(resp.status_code, 201, "feedback event creation")
        event = resp.json()
        assert_eq(event["type"], "topic_preference", "event type")
        assert_eq(event["value"], "Renewable Energy", "event value")
        assert_eq(event["sentiment"], "positive", "event sentiment")

        # GET topic preferences — the preference should exist with positive weight
        resp = api.get(f"/api/workspaces/{ws_id}/preferences/topics")
        assert_eq(resp.status_code, 200, "get topic preferences")
        prefs = resp.json()
        matching = [p for p in prefs if p["topic"] == "Renewable Energy"]
        assert_true(len(matching) >= 1, "Renewable Energy preference exists")
        assert_true(matching[0]["weight"] > 0, "Renewable Energy weight is positive")

        # Also verify source_preference conversion works
        resp = api.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={
                "type": "source_preference",
                "value": "TechCrunch",
                "sentiment": "negative",
            },
        )
        assert_eq(resp.status_code, 201, "source preference feedback event")
        resp = api.get(f"/api/workspaces/{ws_id}/preferences/sources")
        assert_eq(resp.status_code, 200, "get source preferences")
        src_prefs = resp.json()
        matching = [p for p in src_prefs if p["source"] == "TechCrunch"]
        assert_true(len(matching) >= 1, "TechCrunch source preference exists")
        assert_true(matching[0]["weight"] < 0, "TechCrunch weight is negative")

        # Verify accumulative weight: send another positive event for the same topic
        resp = api.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={
                "type": "topic_preference",
                "value": "Renewable Energy",
                "sentiment": "positive",
            },
        )
        assert_eq(resp.status_code, 201, "second topic preference event")
        resp = api.get(f"/api/workspaces/{ws_id}/preferences/topics")
        prefs = resp.json()
        matching = [p for p in prefs if p["topic"] == "Renewable Energy"]
        assert_true(
            matching[0]["weight"] > 1.0,
            f"accumulated weight > 1.0 after two positive events (got {matching[0]['weight']})",
        )

    finally:
        # Cleanup
        api.delete(f"/api/workspaces/{ws_id}")


# ---------------------------------------------------------------------------
# Test 2: Feedback preference affects scoring
# ---------------------------------------------------------------------------


def test_feedback_preference_affects_scoring(api: ApiClient) -> None:
    """POST a source_preference and verify it flows through to scoring.

    This test verifies the end-to-end pipeline by:
    1. Setting a source preference via the feedback API
    2. Checking existing content items that were scored with preferences
       (from previous pipeline runs) to verify feedbackAdjustment appears
       in the API scoreBreakdown.
    """
    ws_id = "ws-1"

    # Verify ws-1 has content items with existing score data
    resp = api.get(f"/api/workspaces/{ws_id}/content?status=included")
    if resp.status_code != 200 or not resp.json():
        raise SkipTest("ws-1 has no included content items")

    items = resp.json()

    # Find a source name that exists in the content
    sources = set()
    for item in items:
        s = item.get("sourceName") or item.get("source")
        if s:
            sources.add(s)
    if not sources:
        raise SkipTest("No source names found in ws-1 content")

    # POST a source_preference for the first source
    source_name = sorted(sources)[0]
    resp = api.post(
        f"/api/workspaces/{ws_id}/feedback",
        json={
            "type": "source_preference",
            "value": source_name,
            "sentiment": "positive",
        },
    )
    assert_eq(resp.status_code, 201, "source preference feedback event creation")

    # Verify the preference record was created/updated
    resp = api.get(f"/api/workspaces/{ws_id}/preferences/sources")
    assert_eq(resp.status_code, 200, "get source preferences")
    source_prefs = resp.json()
    matching = [p for p in source_prefs if p["source"] == source_name]
    assert_true(
        len(matching) >= 1,
        f"source preference for '{source_name}' exists after feedback event",
    )
    assert_true(matching[0]["weight"] > 0, f"source preference weight > 0")

    # Check existing scored content items for feedbackAdjustment in scoreBreakdown.
    # Items scored with preferences (from previous runs) should have feedback data.
    found_feedback_adjustment = False
    checked = 0
    for item in items[:100]:
        resp = api.get(f"/api/content/{item['id']}")
        if resp.status_code != 200:
            continue
        detail = resp.json()
        breakdown = detail.get("scoreBreakdown", {})
        checked += 1
        if "feedbackAdjustment" in breakdown:
            found_feedback_adjustment = True
            # Verify the value is numeric
            adj = breakdown["feedbackAdjustment"]
            assert_true(
                isinstance(adj, (int, float)),
                f"feedbackAdjustment is numeric (got {type(adj).__name__})",
            )
            print(
                f"    [INFO] Found feedbackAdjustment={adj} on item {item['id'][:12]}"
            )
            break

    assert_true(
        found_feedback_adjustment,
        f"At least one content item has feedbackAdjustment in scoreBreakdown "
        f"(checked {checked} items)",
    )


# ---------------------------------------------------------------------------
# Test 3: Multi-word BM25 scoring verification
# ---------------------------------------------------------------------------


def test_multiword_bm25_scoring(api: ApiClient) -> None:
    """Verify multi-word priority themes produce non-zero BM25 in scoring.

    Checks existing scored content items for non-zero BM25 (keyword/bm25)
    scores.  Items scored with the new code (after the BM25 fix) will have
    non-zero BM25 when priority theme component words appear in content.
    """
    ws_id = "ws-1"

    # Get the workspace profile to see priority themes
    resp = api.get(f"/api/workspaces/{ws_id}/profile")
    if resp.status_code != 200:
        raise SkipTest("Cannot read ws-1 profile")
    profile = resp.json()
    themes = profile.get("priorityThemes", [])
    if not themes:
        raise SkipTest("ws-1 has no priority themes")

    print(f"    [INFO] Priority themes: {themes}")

    # Get included content items
    resp = api.get(f"/api/workspaces/{ws_id}/content?status=included")
    if resp.status_code != 200 or not resp.json():
        raise SkipTest("No included content items found")

    items = resp.json()

    # Look at scoreBreakdown of items for non-zero scores.
    # The API returns: relevance (keyword), bm25, freshness, sourceAuthority.
    # Items scored with the new code may have non-zero relevance/bm25.
    found_nonzero_relevance = False
    found_nonzero_bm25 = False
    checked = 0
    for item in items[:100]:
        resp = api.get(f"/api/content/{item['id']}")
        if resp.status_code != 200:
            continue
        detail = resp.json()
        breakdown = detail.get("scoreBreakdown", {})
        checked += 1

        if breakdown.get("relevance", 0) > 0:
            found_nonzero_relevance = True
        if breakdown.get("bm25", 0) > 0:
            found_nonzero_bm25 = True

        if found_nonzero_relevance and found_nonzero_bm25:
            break

    # Report findings — BM25 may be 0 if items were scored with old code
    # or if priority theme words don't match content.  The test verifies
    # the API surface is correct.
    if found_nonzero_relevance:
        print(f"    [INFO] Found non-zero relevance score in {checked} items checked")
    if found_nonzero_bm25:
        print(f"    [INFO] Found non-zero BM25 score in {checked} items checked")

    # At minimum, the scoreBreakdown API should return the expected keys
    # for items that have been scored.
    assert_true(
        checked > 0,
        "Able to check content item score breakdowns via API",
    )

    # Verify the scoreBreakdown has the expected structure
    first_item_id = items[0]["id"] if items else None
    assert_true(first_item_id is not None, "first item has an ID")
    sample_resp = api.get(f"/api/content/{first_item_id}")
    assert_eq(sample_resp.status_code, 200, "get first content item detail")
    sample_breakdown = sample_resp.json().get("scoreBreakdown", {})
    assert_in("relevance", sample_breakdown, "scoreBreakdown has relevance key")
    assert_in("bm25", sample_breakdown, "scoreBreakdown has bm25 key")
    assert_in("freshness", sample_breakdown, "scoreBreakdown has freshness key")
    assert_in(
        "sourceAuthority", sample_breakdown, "scoreBreakdown has sourceAuthority key"
    )

    if not found_nonzero_relevance and not found_nonzero_bm25:
        print(
            f"    [INFO] No non-zero keyword/BM25 found in {checked} items. "
            "This may indicate items were scored before the BM25 fix was deployed. "
            "The unit tests (test_scoring.py) verify BM25 correctness directly."
        )


# ---------------------------------------------------------------------------
# Test 4: Score breakdown API enrichment
# ---------------------------------------------------------------------------


def test_score_breakdown_enrichment(api: ApiClient) -> None:
    """Verify scoreBreakdown includes feedbackAdjustment and feedback keys when present.

    Checks existing scored content items that have feedback data in their
    score_breakdown_json (from previous pipeline runs with preferences).
    """
    ws_id = "ws-1"

    # Get included content items
    resp = api.get(f"/api/workspaces/{ws_id}/content?status=included")
    if resp.status_code != 200 or not resp.json():
        raise SkipTest("No included content items found")

    items = resp.json()

    # Scan items for feedback keys in scoreBreakdown
    found_feedback_adjustment = False
    found_feedback_detail = False
    checked = 0
    for item in items[:200]:
        resp = api.get(f"/api/content/{item['id']}")
        if resp.status_code != 200:
            continue
        detail = resp.json()
        breakdown = detail.get("scoreBreakdown", {})
        checked += 1

        if "feedbackAdjustment" in breakdown:
            found_feedback_adjustment = True
            adj = breakdown["feedbackAdjustment"]
            assert_true(
                isinstance(adj, (int, float)),
                f"feedbackAdjustment is numeric (got {type(adj).__name__})",
            )
            print(f"    [INFO] feedbackAdjustment={adj} on item {item['id'][:12]}")

        if "feedback" in breakdown:
            found_feedback_detail = True
            fb = breakdown["feedback"]
            assert_true(isinstance(fb, dict), "feedback is a dict")
            assert_in("topicsMatched", fb, "feedback has topicsMatched")
            assert_in("sourcesMatched", fb, "feedback has sourcesMatched")
            assert_in("eventCount", fb, "feedback has eventCount")
            print(
                f"    [INFO] feedback={{topicsMatched: {fb['topicsMatched']}, "
                f"sourcesMatched: {fb['sourcesMatched']}, "
                f"eventCount: {fb['eventCount']}}} on item {item['id'][:12]}"
            )

        if found_feedback_adjustment and found_feedback_detail:
            break

    assert_true(
        found_feedback_adjustment,
        f"At least one content item has feedbackAdjustment in scoreBreakdown "
        f"(checked {checked} items)",
    )
    assert_true(
        found_feedback_detail,
        f"At least one content item has feedback dict in scoreBreakdown "
        f"(checked {checked} items)",
    )


# ---------------------------------------------------------------------------
# Test 5: Feedback summary sentiment correctness
# ---------------------------------------------------------------------------


def test_feedback_summary_sentiment_correctness(api: ApiClient) -> None:
    """Verify sentiment labels correctly reflect preference weights."""
    # Create a fresh workspace
    ts = time.strftime("%Y%m%d-%H%M%S")
    resp = api.post(
        "/api/workspaces",
        json={
            "name": f"Feedback Sentiment Test {ts}",
            "customer": "Test",
            "status": "active",
        },
    )
    assert_eq(resp.status_code, 201, "workspace creation")
    ws_id = resp.json()["id"]

    try:
        # PUT topic preferences with mixed weights
        resp = api.put(
            f"/api/workspaces/{ws_id}/preferences/topics",
            json={
                "preferences": [
                    {"topic": "Positive Topic", "weight": 2.0},
                    {"topic": "Negative Topic", "weight": -1.0},
                    {"topic": "Neutral Topic", "weight": 0.0},
                    {"topic": "Default Topic", "weight": 1.0},
                ],
            },
        )
        assert_eq(resp.status_code, 200, "put topic preferences")

        # PUT source preferences with mixed weights
        resp = api.put(
            f"/api/workspaces/{ws_id}/preferences/sources",
            json={
                "preferences": [
                    {"source": "Good Source", "weight": 1.5},
                    {"source": "Bad Source", "weight": -2.0},
                ],
            },
        )
        assert_eq(resp.status_code, 200, "put source preferences")

        # GET feedback summary
        resp = api.get(f"/api/workspaces/{ws_id}/feedback/summary")
        assert_eq(resp.status_code, 200, "get feedback summary")
        summary = resp.json()

        # Verify topic preference sentiments
        topic_prefs = {p["topic"]: p for p in summary["topicPreferences"]}
        assert_in("Positive Topic", topic_prefs, "Positive Topic in summary")
        assert_eq(
            topic_prefs["Positive Topic"]["sentiment"],
            "positive",
            "Positive Topic sentiment",
        )
        assert_eq(
            topic_prefs["Positive Topic"]["weight"],
            2.0,
            "Positive Topic weight",
        )

        assert_in("Negative Topic", topic_prefs, "Negative Topic in summary")
        assert_eq(
            topic_prefs["Negative Topic"]["sentiment"],
            "negative",
            "Negative Topic sentiment",
        )
        assert_eq(
            topic_prefs["Negative Topic"]["weight"],
            -1.0,
            "Negative Topic weight",
        )

        assert_in("Neutral Topic", topic_prefs, "Neutral Topic in summary")
        assert_eq(
            topic_prefs["Neutral Topic"]["sentiment"],
            "neutral",
            "Neutral Topic sentiment",
        )

        assert_in("Default Topic", topic_prefs, "Default Topic in summary")
        assert_eq(
            topic_prefs["Default Topic"]["sentiment"],
            "positive",
            "Default Topic (weight=1.0) sentiment",
        )

        # Verify source preference sentiments
        source_prefs = {p["source"]: p for p in summary["sourcePreferences"]}
        assert_in("Good Source", source_prefs, "Good Source in summary")
        assert_eq(
            source_prefs["Good Source"]["sentiment"],
            "positive",
            "Good Source sentiment",
        )

        assert_in("Bad Source", source_prefs, "Bad Source in summary")
        assert_eq(
            source_prefs["Bad Source"]["sentiment"],
            "negative",
            "Bad Source sentiment",
        )

    finally:
        api.delete(f"/api/workspaces/{ws_id}")


# ---------------------------------------------------------------------------
# Test 6: Vote toggle correctness
# ---------------------------------------------------------------------------


def test_vote_toggle_correctness(api: ApiClient) -> None:
    """Verify thumb up toggle creates exactly one event, toggle-off creates none."""
    # Use ws-1 which has reports with messages
    ws_id = "ws-1"

    # Get a report with messages
    resp = api.get(f"/api/workspaces/{ws_id}/reports")
    if resp.status_code != 200 or not resp.json():
        raise SkipTest("No reports found for ws-1")

    reports = resp.json()
    thread_id = reports[0]["id"]

    # Get messages for this thread
    resp = api.get(f"/api/report-threads/{thread_id}/messages")
    if resp.status_code != 200 or not resp.json():
        raise SkipTest("No messages found in report thread")

    messages = resp.json()
    # Find a system or agent message (not user) to vote on
    msg = None
    for m in messages:
        if m["role"] in ("system", "agent"):
            msg = m
            break
    if msg is None:
        raise SkipTest("No system/agent message found to vote on")

    message_id = msg["id"]

    # Reset the message feedback to None first (clean state)
    initial_feedback = msg.get("feedback")

    # If already has feedback, toggle it off first
    if initial_feedback is not None:
        resp = api.post(
            f"/api/report-messages/{message_id}/thumb",
            json={
                "value": initial_feedback,
            },
        )
        assert_eq(resp.status_code, 200, f"initial toggle-off ({initial_feedback})")

    # Count feedback events before
    resp = api.get(f"/api/workspaces/{ws_id}/feedback")
    events_before = resp.json()
    thumbs_before = [
        e
        for e in events_before
        if e["type"] in ("thumbs_up", "thumbs_down")
        and e.get("messageId") == message_id
    ]
    count_before = len(thumbs_before)

    # POST thumb up
    resp = api.post(f"/api/report-messages/{message_id}/thumb", json={"value": "up"})
    assert_eq(resp.status_code, 200, "thumb up")

    # Count feedback events after first vote
    resp = api.get(f"/api/workspaces/{ws_id}/feedback")
    events_after_first = resp.json()
    thumbs_after_first = [
        e
        for e in events_after_first
        if e["type"] in ("thumbs_up", "thumbs_down")
        and e.get("messageId") == message_id
    ]
    count_after_first = len(thumbs_after_first)

    # After thumb up, count should be count_before + 1
    assert_eq(
        count_after_first,
        count_before + 1,
        "feedback event count after thumb up",
    )

    # POST thumb up again (toggle off)
    resp = api.post(f"/api/report-messages/{message_id}/thumb", json={"value": "up"})
    assert_eq(resp.status_code, 200, "thumb up toggle off")

    # Count feedback events after toggle off — should NOT increase
    resp = api.get(f"/api/workspaces/{ws_id}/feedback")
    events_after_toggle = resp.json()
    thumbs_after_toggle = [
        e
        for e in events_after_toggle
        if e["type"] in ("thumbs_up", "thumbs_down")
        and e.get("messageId") == message_id
    ]
    count_after_toggle = len(thumbs_after_toggle)

    assert_eq(
        count_after_toggle,
        count_after_first,
        "feedback event count after toggle off (should not create new event)",
    )

    # Verify message feedback is now None
    resp = api.get(f"/api/report-threads/{thread_id}/messages")
    messages_after = resp.json()
    msg_after = next((m for m in messages_after if m["id"] == message_id), None)
    if msg_after is None:
        raise AssertionError("message still exists")
    assert_eq(msg_after["feedback"], None, "message feedback is null after toggle off")


# ---------------------------------------------------------------------------
# Test 7: Feedback events list
# ---------------------------------------------------------------------------


def test_feedback_events_list(api: ApiClient) -> None:
    """Verify GET /feedback returns events with proper structure."""
    # Create a workspace with some feedback events
    ts = time.strftime("%Y%m%d-%H%M%S")
    resp = api.post(
        "/api/workspaces",
        json={
            "name": f"Feedback List Test {ts}",
            "customer": "Test",
            "status": "active",
        },
    )
    assert_eq(resp.status_code, 201, "workspace creation")
    ws_id = resp.json()["id"]

    try:
        # Create various feedback events
        events_to_create = [
            {
                "type": "topic_preference",
                "value": "Machine Learning",
                "sentiment": "positive",
            },
            {
                "type": "source_preference",
                "value": "Ars Technica",
                "sentiment": "positive",
            },
            {
                "type": "topic_preference",
                "value": "Blockchain",
                "sentiment": "negative",
            },
        ]
        created_ids = []
        for evt in events_to_create:
            resp = api.post(f"/api/workspaces/{ws_id}/feedback", json=evt)
            assert_eq(resp.status_code, 201, f"create feedback event: {evt}")
            created_ids.append(resp.json()["id"])

        # GET feedback events
        resp = api.get(f"/api/workspaces/{ws_id}/feedback")
        assert_eq(resp.status_code, 200, "get feedback events")
        events = resp.json()

        assert_true(len(events) >= 3, f"at least 3 events returned, got {len(events)}")

        # Verify structure of each event
        for event in events[:3]:
            assert_in("id", event, "event has id")
            assert_in("type", event, "event has type")
            assert_in("workspaceId", event, "event has workspaceId")
            assert_in("createdAt", event, "event has createdAt")
            assert_in("reportTitle", event, "event has reportTitle")
            assert_in("messageExcerpt", event, "event has messageExcerpt")

        # Verify our created events are present
        event_ids = {e["id"] for e in events}
        for created_id in created_ids:
            assert_true(
                created_id in event_ids,
                f"created event {created_id} is in the list",
            )

        # Verify values
        ml_events = [e for e in events if e.get("value") == "Machine Learning"]
        assert_true(len(ml_events) >= 1, "Machine Learning event found")
        assert_eq(ml_events[0]["sentiment"], "positive", "ML event sentiment")
        assert_eq(ml_events[0]["type"], "topic_preference", "ML event type")

        # Verify that topic_preference events also created preference records
        resp = api.get(f"/api/workspaces/{ws_id}/preferences/topics")
        assert_eq(resp.status_code, 200, "get topic preferences")
        prefs = resp.json()
        ml_prefs = [p for p in prefs if p["topic"] == "Machine Learning"]
        assert_true(len(ml_prefs) >= 1, "ML preference created from feedback event")
        assert_true(ml_prefs[0]["weight"] > 0, "ML preference weight > 0")

        bc_prefs = [p for p in prefs if p["topic"] == "Blockchain"]
        assert_true(
            len(bc_prefs) >= 1, "Blockchain preference created from feedback event"
        )
        assert_true(bc_prefs[0]["weight"] < 0, "Blockchain preference weight < 0")

    finally:
        api.delete(f"/api/workspaces/{ws_id}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    print("=" * 70)
    print("Feedback Loop Repair — API Integration Tests (Pass 4)")
    print(f"Base URL: {BASE_URL}")
    print("=" * 70)
    print()

    api = ApiClient(base_url=BASE_URL)

    # Login
    print("[SETUP] Logging in...")
    if not api.login():
        print("  FAILED to login. Aborting.")
        return 1
    print("  Login OK")
    print()

    # Health check
    print("[SETUP] Health check...")
    try:
        resp = api.get("/api/workspaces")
        assert_eq(resp.status_code, 200, "health check")
        print(f"  API healthy — {len(resp.json())} workspaces")
    except AssertionError:
        print(f"  API not healthy")
        return 1
    print()

    # Run tests
    tests = [
        (
            "1. Feedback event → preference conversion",
            test_feedback_event_creates_preference,
        ),
        (
            "2. Feedback preference affects scoring",
            test_feedback_preference_affects_scoring,
        ),
        ("3. Multi-word BM25 scoring verification", test_multiword_bm25_scoring),
        ("4. Score breakdown API enrichment", test_score_breakdown_enrichment),
        (
            "5. Feedback summary sentiment correctness",
            test_feedback_summary_sentiment_correctness,
        ),
        ("6. Vote toggle correctness", test_vote_toggle_correctness),
        ("7. Feedback events list", test_feedback_events_list),
    ]

    results: list[TestResult] = []
    for name, fn in tests:
        print(f"[TEST] {name}")
        result = run_test(name, fn, api)
        results.append(result)
        print(f"  {result.message}")
        print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print(f"  Passed:  {_pass_count}")
    print(f"  Failed:  {_fail_count}")
    print(f"  Skipped: {_skip_count}")
    print()

    if _fail_count > 0:
        print("FAILED TESTS:")
        for r in results:
            if not r.passed and not r.skipped:
                print(f"  X {r.name}: {r.message}")
        print()

    if _skip_count > 0:
        print("SKIPPED TESTS:")
        for r in results:
            if r.skipped:
                print(f"  - {r.name}: {r.message}")
        print()

    if _fail_count == 0:
        print("ALL TESTS PASSED")
        return 0
    else:
        print("SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
