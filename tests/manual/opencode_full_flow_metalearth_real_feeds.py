#!/usr/bin/env python3
"""Manual deployed-stack full-flow QA for the Metal Earth client scenario using the mandatory OpenCode path.

This script is intentionally NOT part of CI.

It performs a real end-to-end validation against a deployed stack,
tailored for the Metal Earth client persona:
1. Login
2. Create a fresh workspace
3. Configure profile/settings for Metal Earth-specific ingestion
4. Add and test real public RSS feeds relevant to Metal Earth's market
5. Trigger run-now and poll until completion
6. Verify report generation with sources
7. Regenerate the report
8. Send one report-thread chat message and verify agent reply relevance

Environment variables:
- ``SME_BASE_URL``: default ``http://127.0.0.1:8000/api``
- ``SME_USERNAME``: default ``admin``
- ``SME_PASSWORD``: default ``admin``
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from http.cookiejar import CookieJar


BASE_URL = os.environ.get("SME_BASE_URL", "http://127.0.0.1:8000/api").rstrip("/")
USERNAME = os.environ.get("SME_USERNAME", "admin")
PASSWORD = os.environ.get("SME_PASSWORD", "admin")

# Google News RSS feeds relevant to Metal Earth's market segments:
# licensed collectibles, model kits, toy industry, aviation, architecture,
# and entertainment franchises.
REAL_FEEDS: list[dict[str, str]] = [
    {
        "name": "Google News - licensed products collectibles",
        "url": "https://news.google.com/rss/search?q=licensed+products+collectibles+hobby",
        "type": "rss",
        "cadence": "daily",
    },
    {
        "name": "Google News - model kits hobby retail",
        "url": "https://news.google.com/rss/search?q=model+kits+hobby+retail",
        "type": "rss",
        "cadence": "daily",
    },
    {
        "name": "Google News - toy industry collectibles",
        "url": "https://news.google.com/rss/search?q=toy+industry+collectibles",
        "type": "rss",
        "cadence": "daily",
    },
    {
        "name": "Google News - aviation aerospace",
        "url": "https://news.google.com/rss/search?q=aviation+aerospace",
        "type": "rss",
        "cadence": "daily",
    },
    {
        "name": "Google News - architecture landmarks",
        "url": "https://news.google.com/rss/search?q=architecture+landmarks",
        "type": "rss",
        "cadence": "daily",
    },
    {
        "name": "Google News - entertainment franchise releases",
        "url": "https://news.google.com/rss/search?q=entertainment+franchise+release",
        "type": "rss",
        "cadence": "daily",
    },
]


class QaError(RuntimeError):
    """Raised when manual QA verification fails."""


@dataclass
class ApiClient:
    base_url: str

    def __post_init__(self) -> None:
        self._jar = CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._jar)
        )

    def request(
        self, method: str, path: str, body: dict | None = None
    ) -> tuple[int, dict]:
        payload = None
        headers: dict[str, str] = {}
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(
            self.base_url + path,
            data=payload,
            headers=headers,
            method=method,
        )
        try:
            with self._opener.open(req, timeout=600) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw) if raw else {}
                return resp.status, data
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                data = {"detail": raw}
            return exc.code, data


def require(condition: bool, message: str) -> None:
    if not condition:
        raise QaError(message)


def summarize_step(step: dict) -> str:
    return (
        f"{step.get('name')} status={step.get('status')} "
        f"error={step.get('error')} details={step.get('details')}"
    )


def main() -> int:
    client = ApiClient(BASE_URL)
    print(f"Using API base: {BASE_URL}")

    # ── Step 1: Login ───────────────────────────────────────────────────
    status, login = client.request(
        "POST",
        "/session/login",
        {"username": USERNAME, "password": PASSWORD},
    )
    require(status == 200, f"Login failed: {status} {login}")
    print("Login OK")

    # ── Step 2: Create workspace ────────────────────────────────────────
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    status, workspace = client.request(
        "POST",
        "/workspaces",
        {
            "name": f"Metal Earth QA {ts}",
            "customer": "Metal Earth",
            "status": "active",
        },
    )
    require(status == 201, f"Workspace creation failed: {status} {workspace}")
    workspace_id = workspace["id"]
    print(f"Workspace created: {workspace_id}")

    # ── Step 3: Update profile ──────────────────────────────────────────
    profile = {
        "businessName": "Metal Earth",
        "description": (
            "Metal Earth is a 3D metal model kit brand focused on licensed pop culture models, "
            "aviation, architecture, vehicles, space, and collectible hobby products."
        ),
        "products": [
            "3D metal model kits",
            "licensed collectible hobby kits",
            "aviation model kits",
            "architecture model kits",
            "pop culture franchise model kits",
        ],
        "competitors": [
            "Piececool",
            "UGEARS",
            "Fascinations competitors",
            "collectible model kit brands",
        ],
        "priorityThemes": [
            "licensed products",
            "franchise entertainment",
            "collectibles",
            "hobby retail",
            "model kits",
            "aviation",
            "architecture",
            "space",
            "toy industry",
            "gift products",
            "fandom",
        ],
        "excludedTopics": [
            "cryptocurrency",
            "enterprise SaaS",
            "general software engineering",
            "pure B2B cloud infrastructure",
        ],
        "notes": (
            "The report should prioritize new licensed IP/franchise developments, "
            "hobby/collectibles retail signals, product inspiration themes relevant to "
            "Metal Earth's categories, and major entertainment or aerospace/architecture "
            "news that could inform future product opportunities."
        ),
    }

    status, profile_resp = client.request(
        "PUT",
        f"/workspaces/{workspace_id}/profile",
        profile,
    )
    require(status == 200, f"Profile update failed: {status} {profile_resp}")
    print("Profile updated OK")

    # ── Step 4: Update settings ─────────────────────────────────────────
    settings = {
        "reportStyle": "detailed",
        "thresholds": {
            "minRelevanceScore": 0.0,
            "minFinalScore": 0.0,
            "maxArticlesPerReport": 10,
        },
        "schedule": {
            "enabled": False,
            "frequency": "daily",
            "timeOfDay": "08:00",
            "timezone": "UTC",
        },
    }

    status, settings_resp = client.request(
        "PUT",
        f"/workspaces/{workspace_id}/settings",
        settings,
    )
    require(status == 200, f"Settings update failed: {status} {settings_resp}")
    print("Settings updated OK")

    # ── Step 5: Add & test feeds ────────────────────────────────────────
    successful_feeds: list[dict] = []
    for feed in REAL_FEEDS:
        status, created = client.request(
            "POST",
            f"/workspaces/{workspace_id}/feeds",
            feed,
        )
        require(
            status == 201, f"Feed creation failed for {feed['url']}: {status} {created}"
        )
        feed_id = created["id"]
        print(f"Feed created: {feed['name']} ({feed_id})")

        status, tested = client.request("POST", f"/feeds/{feed_id}/test")
        require(
            status == 200, f"Feed test request failed for {feed_id}: {status} {tested}"
        )
        if tested.get("success"):
            print(
                f"Feed OK: {feed['name']} articlesFound={tested.get('articlesFound')} "
                f"sourceTitle={tested.get('sourceTitle')}"
            )
            successful_feeds.append(
                {"id": feed_id, "name": feed["name"], "test": tested}
            )
            continue

        print(
            f"Feed failed and will be removed: {feed['name']} error={tested.get('lastError')}"
        )
        delete_status, deleted = client.request("DELETE", f"/feeds/{feed_id}")
        require(
            delete_status == 200,
            f"Failed to delete unsuccessful feed {feed_id}: {delete_status} {deleted}",
        )

    require(
        successful_feeds, "No real feeds passed validation; cannot run full-flow QA"
    )
    print(f"Feeds ready: {len(successful_feeds)} successful")

    # ── Step 6: Run-now (with polling) ──────────────────────────────────
    status, run = client.request("POST", f"/workspaces/{workspace_id}/run-now", {})
    require(status == 201, f"run-now failed: {status} {run}")
    run_id = run["id"]
    print(f"Run created: {run_id} status={run.get('status')}")

    # Poll until the run reaches a terminal state.
    POLL_TIMEOUT = 300  # seconds
    POLL_INTERVAL = 10  # seconds
    elapsed = 0
    run_status = run.get("status", "pending")
    while (
        run_status not in ("success", "failed", "cancelled") and elapsed < POLL_TIMEOUT
    ):
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        status, detail = client.request("GET", f"/runs/{run_id}")
        require(status == 200, f"Run detail failed during polling: {status} {detail}")
        run_status = detail.get("status", "unknown")
        print(f"  polling ... run {run_id} status={run_status} elapsed={elapsed}s")

    require(
        run_status == "success",
        f"Run did not reach success status (got '{run_status}') within {POLL_TIMEOUT}s",
    )
    print(f"Run completed successfully: {run_id}")

    # ── Step 7: Verify run metadata ─────────────────────────────────────
    status, detail = client.request("GET", f"/runs/{run_id}")
    require(status == 200, f"Run detail failed: {status} {detail}")
    for step in detail.get("steps", []):
        print("Step:", summarize_step(step))

    fetch_step = next(step for step in detail["steps"] if step["name"] == "fetch_feeds")
    fetch_meta = fetch_step.get("metadata", {})
    require(
        int(fetch_meta.get("feedsSucceeded", 0)) >= 1,
        f"Expected at least one successful feed in fetch metadata: {fetch_meta}",
    )
    require(
        int(fetch_meta.get("entriesImported", 0)) >= 1,
        f"Expected imported entries in fetch metadata: {fetch_meta}",
    )
    print(
        f"Fetch metadata OK: feedsSucceeded={fetch_meta.get('feedsSucceeded')} entriesImported={fetch_meta.get('entriesImported')}"
    )

    # ── Step 8: Verify report ───────────────────────────────────────────
    report_ids = detail.get("links", {}).get("reports") or []
    require(report_ids, f"Expected generated report link in run detail: {detail}")
    report_id = report_ids[0]
    print(f"Report created: {report_id}")

    status, messages = client.request("GET", f"/report-threads/{report_id}/messages")
    require(status == 200, f"Report messages failed: {status} {messages}")
    system_messages = [msg for msg in messages if msg.get("role") == "system"]
    require(system_messages, "Expected at least one system report message")
    report_message = system_messages[-1]
    sources = (report_message.get("metadata") or {}).get("sources") or []
    require(sources, f"Expected report sources, got none: {report_message}")
    require(
        "No SME news items were provided" not in report_message.get("content", ""),
        "Report content indicates empty input even though feeds imported content",
    )
    print(f"System report message has {len(sources)} sources")

    # ── Step 9: Keyword relevance check (soft) ──────────────────────────
    report_content = report_message.get("content", "").lower()
    report_keywords = [
        "licensed",
        "collectible",
        "hobby",
        "model",
        "aviation",
        "architecture",
        "franchise",
        "retail",
        "entertainment",
    ]
    report_keyword_matches = [kw for kw in report_keywords if kw in report_content]
    if report_keyword_matches:
        print(f"Report keyword relevance OK: matched {report_keyword_matches}")
    else:
        print(
            f"WARNING: Report content matched none of the expected Metal Earth keywords: {report_keywords}"
        )
        print("  This is a soft check — continuing anyway.")

    # ── Step 10: Verify source items ────────────────────────────────────
    checked_source_count = 0
    for source_id in sources[:3]:
        status, content = client.request("GET", f"/content/{source_id}")
        require(
            status == 200,
            f"Source item {source_id} failed to resolve: {status} {content}",
        )
        checked_source_count += 1
    require(checked_source_count >= 1, "Expected at least one resolvable source item")
    print(
        f"Source items validated: {checked_source_count}/{min(len(sources), 3)} resolved"
    )

    # ── Step 11: Regenerate ─────────────────────────────────────────────
    status, regenerated = client.request("POST", f"/reports/{report_id}/regenerate", {})
    require(status == 200, f"Report regenerate failed: {status} {regenerated}")
    require(
        regenerated.get("role") == "system",
        f"Unexpected regenerate payload: {regenerated}",
    )
    print(f"Regenerate OK: message={regenerated.get('id')}")

    # ── Step 12: Chat message ───────────────────────────────────────────
    status, chat = client.request(
        "POST",
        f"/report-threads/{report_id}/messages",
        {
            "content": "Summarize the most important opportunities or market signals for Metal Earth from this report."
        },
    )
    require(status == 201, f"Report chat failed: {status} {chat}")
    require(chat.get("agentMessage"), f"Expected agentMessage from report chat: {chat}")
    require(
        ((chat["agentMessage"].get("metadata") or {}).get("opencodeSessionId")),
        f"Expected opencodeSessionId metadata in chat response: {chat}",
    )
    agent_message_id = chat["agentMessage"]["id"]
    print(f"Chat OK: agentMessage={agent_message_id}")

    # ── Step 13: Agent reply relevance check (soft) ─────────────────────
    agent_content = (chat["agentMessage"].get("content") or "").lower()
    agent_keywords = [
        "opportunity",
        "product",
        "licensing",
        "collectible",
        "market",
        "franchise",
    ]
    agent_keyword_matches = [kw for kw in agent_keywords if kw in agent_content]
    if agent_keyword_matches:
        print(f"Agent reply relevance OK: matched {agent_keyword_matches}")
    else:
        print(
            f"WARNING: Agent reply matched none of the expected keywords: {agent_keywords}"
        )

    # ── Step 14: Print summary JSON ─────────────────────────────────────
    print("\nManual full-flow OpenCode QA PASSED (Metal Earth)")
    print(
        json.dumps(
            {
                "workspaceId": workspace_id,
                "runId": run_id,
                "reportId": report_id,
                "successfulFeedIds": [feed["id"] for feed in successful_feeds],
                "feedNames": [feed["name"] for feed in successful_feeds],
                "reportSourceCount": len(sources),
                "validatedSourceCount": checked_source_count,
                "reportKeywordMatches": report_keyword_matches,
                "chatAgentMessageId": agent_message_id,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except QaError as exc:
        print(f"MANUAL QA FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
