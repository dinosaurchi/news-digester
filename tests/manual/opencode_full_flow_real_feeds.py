#!/usr/bin/env python3
"""Manual deployed-stack full-flow QA for the mandatory OpenCode path.

This script is intentionally NOT part of CI.

It performs a real end-to-end validation against a deployed stack:
1. Login
2. Create a fresh workspace
3. Configure profile/settings for permissive ingestion
4. Add and test real public RSS feeds
5. Trigger run-now
6. Verify report generation with sources
7. Regenerate the report
8. Send one report-thread chat message

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

# Prefer feeds that are usually stable and parseable. The script tests each
# feed before relying on it and deletes failed feeds from the workspace.
REAL_FEEDS: list[dict[str, str]] = [
    {
        "name": "Hacker News Frontpage",
        "url": "https://hnrss.org/frontpage",
        "type": "rss",
        "cadence": "daily",
    },
    {
        "name": "Lobsters",
        "url": "https://lobste.rs/rss",
        "type": "rss",
        "cadence": "daily",
    },
    {
        "name": "Planet Python",
        "url": "https://planetpython.org/rss20.xml",
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

    def request(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
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
            with self._opener.open(req, timeout=180) as resp:
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

    status, login = client.request(
        "POST",
        "/session/login",
        {"username": USERNAME, "password": PASSWORD},
    )
    require(status == 200, f"Login failed: {status} {login}")
    print("Login OK")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    status, workspace = client.request(
        "POST",
        "/workspaces",
        {
            "name": f"Manual OpenCode E2E {ts}",
            "customer": "Manual QA Customer",
            "status": "active",
        },
    )
    require(status == 201, f"Workspace creation failed: {status} {workspace}")
    workspace_id = workspace["id"]
    print(f"Workspace created: {workspace_id}")

    status, profile = client.request(
        "PUT",
        f"/workspaces/{workspace_id}/profile",
        {
            "businessName": "Manual QA Customer",
            "description": "Manual full-flow OpenCode QA workspace",
            "products": ["news intelligence"],
            "competitors": [],
            "priorityThemes": [
                "AI",
                "LLM",
                "cloud",
                "security",
                "open source",
                "startup",
                "funding",
                "engineering",
            ],
            "excludedTopics": [],
            "notes": "Created by manual full-flow deployed-stack QA script.",
        },
    )
    require(status == 200, f"Profile update failed: {status} {profile}")

    status, settings = client.request(
        "PUT",
        f"/workspaces/{workspace_id}/settings",
        {
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
        },
    )
    require(status == 200, f"Settings update failed: {status} {settings}")

    successful_feeds: list[dict] = []
    for feed in REAL_FEEDS:
        status, created = client.request(
            "POST",
            f"/workspaces/{workspace_id}/feeds",
            feed,
        )
        require(status == 201, f"Feed creation failed for {feed['url']}: {status} {created}")
        feed_id = created["id"]
        print(f"Feed created: {feed['name']} ({feed_id})")

        status, tested = client.request("POST", f"/feeds/{feed_id}/test")
        require(status == 200, f"Feed test request failed for {feed_id}: {status} {tested}")
        if tested.get("success"):
            print(
                f"Feed OK: {feed['name']} articlesFound={tested.get('articlesFound')} "
                f"sourceTitle={tested.get('sourceTitle')}"
            )
            successful_feeds.append({"id": feed_id, "name": feed["name"], "test": tested})
            continue

        print(f"Feed failed and will be removed: {feed['name']} error={tested.get('lastError')}")
        delete_status, deleted = client.request("DELETE", f"/feeds/{feed_id}")
        require(
            delete_status == 200,
            f"Failed to delete unsuccessful feed {feed_id}: {delete_status} {deleted}",
        )

    require(successful_feeds, "No real feeds passed validation; cannot run full-flow QA")

    status, run = client.request("POST", f"/workspaces/{workspace_id}/run-now", {})
    require(status == 201, f"run-now failed: {status} {run}")
    run_id = run["id"]
    print(f"Run created: {run_id} status={run.get('status')}")

    status, detail = client.request("GET", f"/runs/{run_id}")
    require(status == 200, f"Run detail failed: {status} {detail}")
    require(detail.get("status") == "success", f"Run not successful: {detail}")
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

    # Verify a few source items resolve.
    checked_source_count = 0
    for source_id in sources[:3]:
        status, content = client.request("GET", f"/content/{source_id}")
        require(status == 200, f"Source item {source_id} failed to resolve: {status} {content}")
        checked_source_count += 1
    require(checked_source_count >= 1, "Expected at least one resolvable source item")

    status, regenerated = client.request("POST", f"/reports/{report_id}/regenerate", {})
    require(status == 200, f"Report regenerate failed: {status} {regenerated}")
    require(regenerated.get("role") == "system", f"Unexpected regenerate payload: {regenerated}")
    print(f"Regenerate OK: message={regenerated.get('id')}")

    status, chat = client.request(
        "POST",
        f"/report-threads/{report_id}/messages",
        {"content": "Summarize the most important developments from this report."},
    )
    require(status == 201, f"Report chat failed: {status} {chat}")
    require(chat.get("agentMessage"), f"Expected agentMessage from report chat: {chat}")
    require(
        ((chat["agentMessage"].get("metadata") or {}).get("opencodeSessionId")),
        f"Expected opencodeSessionId metadata in chat response: {chat}",
    )
    print(f"Chat OK: agentMessage={chat['agentMessage']['id']}")

    print("\nManual full-flow OpenCode QA PASSED")
    print(json.dumps(
        {
            "workspaceId": workspace_id,
            "runId": run_id,
            "reportId": report_id,
            "successfulFeedIds": [feed["id"] for feed in successful_feeds],
            "feedNames": [feed["name"] for feed in successful_feeds],
            "reportSourceCount": len(sources),
        },
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except QaError as exc:
        print(f"MANUAL QA FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
