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
