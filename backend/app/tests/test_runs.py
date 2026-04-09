"""Tests for runs API endpoints."""

from datetime import datetime, timezone


def _create_workspace(client):
    """Helper to create a workspace and return its ID."""
    resp = client.post("/api/workspaces", json={"name": "Runs WS", "customer": "Co"})
    return resp.json()["id"]


def _create_run(client, workspace_id, **overrides):
    """Helper to create a processing run via direct DB insert."""
    from app.tests.conftest import TestingSessionLocal
    from app.models.run import ProcessingRun

    defaults = {
        "id": overrides.pop("id", None),
        "workspace_id": workspace_id,
        "run_type": "manual",
        "status": "success",
        "started_at": datetime(2024, 3, 20, 8, 0, 0, tzinfo=timezone.utc),
        "finished_at": datetime(2024, 3, 20, 8, 5, 0, tzinfo=timezone.utc),
        "duration_ms": 300000,
        "affected_counts_json": {"feeds": 5, "articles": 42, "reports": 1},
    }
    defaults.update(overrides)

    db = TestingSessionLocal()
    try:
        run = ProcessingRun(**defaults)
        db.add(run)
        db.commit()
        run_id = run.id
    finally:
        db.close()
    return run_id


def _create_run_event(client, run_id, **overrides):
    """Helper to create a processing run event via direct DB insert."""
    from app.tests.conftest import TestingSessionLocal
    from app.models.run import ProcessingRunEvent

    defaults = {
        "id": overrides.pop("id", None),
        "run_id": run_id,
        "step_name": "fetch_feeds",
        "status": "success",
        "message": "Fetched 5 feeds successfully",
    }
    defaults.update(overrides)

    db = TestingSessionLocal()
    try:
        event = ProcessingRunEvent(**defaults)
        db.add(event)
        db.commit()
        event_id = event.id
    finally:
        db.close()
    return event_id


def _create_feed(client, workspace_id, **overrides):
    """Helper to create a feed source via direct DB insert."""
    from app.tests.conftest import TestingSessionLocal
    from app.models.feed import FeedSource

    defaults = {
        "id": overrides.pop("id", None),
        "workspace_id": workspace_id,
        "name": "Test Feed",
        "url": overrides.pop("url", "https://example.com/feed.xml"),
        "type": "rss",
        "status": "healthy",
    }
    defaults.update(overrides)

    db = TestingSessionLocal()
    try:
        feed = FeedSource(**defaults)
        db.add(feed)
        db.commit()
        feed_id = feed.id
    finally:
        db.close()
    return feed_id


class TestListRuns:
    """GET /api/workspaces/{workspace_id}/runs"""

    def test_list_runs_empty(self, client):
        """Workspace with no runs → empty list."""
        ws_id = _create_workspace(client)

        resp = client.get(f"/api/workspaces/{ws_id}/runs")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_runs_with_data(self, client):
        """Workspace with runs → returns list."""
        ws_id = _create_workspace(client)
        _create_run(client, ws_id, run_type="manual")
        _create_run(client, ws_id, run_type="scheduled")

        resp = client.get(f"/api/workspaces/{ws_id}/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        types = [r["type"] for r in data]
        assert "manual" in types
        assert "scheduled" in types

    def test_list_runs_filter_status(self, client):
        """Filter by status returns only matching runs."""
        ws_id = _create_workspace(client)
        _create_run(client, ws_id, status="success")
        _create_run(client, ws_id, status="failed")
        _create_run(client, ws_id, status="running")

        resp = client.get(f"/api/workspaces/{ws_id}/runs?status=failed")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "failed"

    def test_list_runs_filter_type(self, client):
        """Filter by type returns only matching runs."""
        ws_id = _create_workspace(client)
        _create_run(client, ws_id, run_type="manual")
        _create_run(client, ws_id, run_type="scheduled")

        resp = client.get(f"/api/workspaces/{ws_id}/runs?type=manual")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["type"] == "manual"

    def test_list_runs_filter_date_range(self, client):
        """Filter by dateFrom and dateTo returns runs in range."""
        ws_id = _create_workspace(client)
        _create_run(
            client,
            ws_id,
            started_at=datetime(2024, 1, 15, 8, 0, 0, tzinfo=timezone.utc),
        )
        _create_run(
            client,
            ws_id,
            started_at=datetime(2024, 3, 20, 8, 0, 0, tzinfo=timezone.utc),
        )

        resp = client.get(
            f"/api/workspaces/{ws_id}/runs"
            f"?dateFrom=2024-03-01T00:00:00Z"
            f"&dateTo=2024-03-31T23:59:59Z"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

    def test_runs_workspace_404(self, client):
        """Workspace doesn't exist → 404."""
        resp = client.get("/api/workspaces/nonexistent-id/runs")
        assert resp.status_code == 404


class TestRunNow:
    """POST /api/workspaces/{workspace_id}/run-now"""

    def test_run_now_creates_run(self, client):
        """Triggering run-now creates a ProcessingRun record."""
        ws_id = _create_workspace(client)

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["workspaceId"] == ws_id
        assert data["type"] == "manual"
        assert data["status"] == "success"
        assert data["startedAt"] is not None
        assert data["completedAt"] is not None
        assert data["durationMs"] is not None
        assert data["error"] is None

    def test_run_now_workspace_404(self, client):
        """Triggering run-now for nonexistent workspace → 404."""
        resp = client.post("/api/workspaces/nonexistent-id/run-now")
        assert resp.status_code == 404

    def test_run_now_creates_events(self, client):
        """Run-now creates 5 pipeline step events."""
        ws_id = _create_workspace(client)

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 201
        run_id = resp.json()["id"]

        # Verify events were created by fetching run detail
        detail_resp = client.get(f"/api/runs/{run_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert len(detail["steps"]) == 5
        step_names = [s["name"] for s in detail["steps"]]
        assert "fetch_feeds" in step_names
        assert "normalize_content" in step_names
        assert "cluster_content" in step_names
        assert "score_content" in step_names
        assert "generate_report" in step_names

    def test_run_now_completes_successfully(self, client):
        """Run completes with success status and correct affected counts.

        With no feeds in the test DB the pipeline fetches 0 feeds and
        creates 0 articles, but still generates 1 report.
        """
        ws_id = _create_workspace(client)

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 201
        data = resp.json()

        assert data["status"] == "success"
        assert data["affectedCounts"]["feeds"] == 0
        assert data["affectedCounts"]["articles"] == 0
        assert data["affectedCounts"]["reports"] == 1

    def test_run_now_all_events_success(self, client):
        """All pipeline events are marked as success/completed after run-now."""
        ws_id = _create_workspace(client)

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 201
        run_id = resp.json()["id"]

        detail_resp = client.get(f"/api/runs/{run_id}")
        assert detail_resp.status_code == 200
        steps = detail_resp.json()["steps"]
        for step in steps:
            assert step["status"] in ("success", "completed")

    def test_run_now_events_have_messages(self, client):
        """Pipeline events have descriptive messages after completion."""
        ws_id = _create_workspace(client)

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        run_id = resp.json()["id"]

        detail_resp = client.get(f"/api/runs/{run_id}")
        steps = detail_resp.json()["steps"]
        messages = {s["name"]: s["details"] for s in steps}
        assert "Fetched" in messages["fetch_feeds"]
        assert "Normalized" in messages["normalize_content"]
        assert "Scored" in messages["score_content"]
        assert "Generated" in messages["generate_report"]

    def test_run_now_creates_multiple_runs(self, client):
        """Multiple run-now calls create separate runs."""
        ws_id = _create_workspace(client)

        resp1 = client.post(f"/api/workspaces/{ws_id}/run-now")
        resp2 = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["id"] != resp2.json()["id"]

    def test_run_now_appears_in_runs_list(self, client):
        """A run-now run appears in the workspace runs list."""
        ws_id = _create_workspace(client)

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        run_id = resp.json()["id"]

        list_resp = client.get(f"/api/workspaces/{ws_id}/runs")
        assert list_resp.status_code == 200
        run_ids = [r["id"] for r in list_resp.json()]
        assert run_id in run_ids

    def test_run_now_log_snippets(self, client):
        """Run detail has log snippets from the pipeline events."""
        ws_id = _create_workspace(client)

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        run_id = resp.json()["id"]

        detail_resp = client.get(f"/api/runs/{run_id}")
        snippets = detail_resp.json()["logSnippets"]
        assert len(snippets) == 5
        assert any("fetch_feeds" in s for s in snippets)

    def test_run_now_links_created_content_items(self, client, monkeypatch):
        """Run detail exposes content item links created during the run."""
        ws_id = _create_workspace(client)
        _create_feed(client, ws_id, url="https://example.com/feed.xml")

        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: [
                {
                    "title": "Fetched article",
                    "url": "https://example.com/article",
                    "source_name": "Example Feed",
                    "published_at": datetime(2024, 3, 20, 8, 0, 0, tzinfo=timezone.utc),
                    "author": "Author",
                    "summary": "Summary",
                    "content": "Body",
                }
            ],
        )

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 201
        run_id = resp.json()["id"]

        detail_resp = client.get(f"/api/runs/{run_id}")
        assert detail_resp.status_code == 200
        content_ids = detail_resp.json()["links"]["contentItems"]
        assert content_ids is not None
        assert isinstance(content_ids, list)
        assert len(content_ids) == 1


class TestGetRunDetail:
    """GET /api/runs/{run_id}"""

    def test_get_run_detail(self, client):
        """Returns run detail with steps, logSnippets, and links."""
        ws_id = _create_workspace(client)
        run_id = _create_run(client, ws_id)
        _create_run_event(
            client, run_id, step_name="fetch_feeds", message="Fetched feeds"
        )

        resp = client.get(f"/api/runs/{run_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == run_id
        assert "steps" in data
        assert "logSnippets" in data
        assert "links" in data

    def test_get_run_detail_with_steps(self, client):
        """Run with multiple events returns all as steps."""
        ws_id = _create_workspace(client)
        run_id = _create_run(client, ws_id)
        _create_run_event(
            client, run_id, step_name="fetch_feeds", message="Fetched 5 feeds"
        )
        _create_run_event(
            client, run_id, step_name="score_articles", message="Scored 42 articles"
        )
        _create_run_event(
            client, run_id, step_name="generate_report", message="Generated 1 report"
        )

        resp = client.get(f"/api/runs/{run_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["steps"]) == 3
        step_names = [s["name"] for s in data["steps"]]
        assert "fetch_feeds" in step_names
        assert "score_articles" in step_names
        assert "generate_report" in step_names
        assert len(data["logSnippets"]) == 3

    def test_get_run_not_found(self, client):
        """Non-existent run → 404."""
        resp = client.get("/api/runs/nonexistent-id")
        assert resp.status_code == 404

    def test_run_detail_camel_case(self, client):
        """Response uses camelCase keys matching frontend contract."""
        ws_id = _create_workspace(client)
        run_id = _create_run(
            client,
            ws_id,
            affected_counts_json={"feeds": 3, "articles": 20, "reports": 1},
            error_summary="Some error",
        )

        resp = client.get(f"/api/runs/{run_id}")
        assert resp.status_code == 200
        data = resp.json()
        # Verify camelCase keys
        assert "workspaceId" in data
        assert "startedAt" in data
        assert "completedAt" in data
        assert "durationMs" in data
        assert "affectedCounts" in data
        assert data["affectedCounts"]["feeds"] == 3
        assert data["affectedCounts"]["articles"] == 20
        assert data["affectedCounts"]["reports"] == 1
        assert data["error"] == "Some error"
