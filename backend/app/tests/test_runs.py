"""Tests for runs API endpoints."""

from datetime import datetime, timedelta, timezone

from app.services.pipeline_steps import FeedFetchResult


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


def _create_workspace_profile(client, workspace_id, **overrides):
    """Helper to create a workspace profile via direct DB insert."""
    from app.tests.conftest import TestingSessionLocal
    from app.models.workspace import WorkspaceProfile

    defaults = {
        "id": overrides.pop("id", None),
        "workspace_id": workspace_id,
        "business_name": "Test Business",
        "description": "Test Description",
        "products": ["Product A"],
        "competitors": ["CompetitorCorp"],
        "priority_themes": overrides.pop("priority_themes", ["AI", "machine learning"]),
        "excluded_topics": overrides.pop("excluded_topics", []),
        "notes": None,
    }
    defaults.update(overrides)

    db = TestingSessionLocal()
    try:
        profile = WorkspaceProfile(**defaults)
        db.add(profile)
        db.commit()
        profile_id = profile.id
    finally:
        db.close()
    return profile_id


def _create_workspace_settings(client, workspace_id, **overrides):
    """Helper to create workspace settings via direct DB insert."""
    from app.tests.conftest import TestingSessionLocal
    from app.models.workspace import WorkspaceSettings

    defaults = {
        "id": overrides.pop("id", None),
        "workspace_id": workspace_id,
        "schedule": {
            "enabled": False,
            "frequency": "daily",
            "timeOfDay": "08:00",
            "timezone": "UTC",
        },
        "report_style": "detailed",
        "thresholds": overrides.pop(
            "thresholds",
            {
                "min_relevance_score": 0.1,
                "min_final_score": 0.1,
                "max_articles_per_report": 15,
            },
        ),
        "retention": {
            "contentDays": 90,
            "reportDays": 365,
            "runHistoryDays": 180,
        },
        "email_delivery": {
            "enabled": False,
            "recipients": [],
            "subjectPrefix": "[Intel Report]",
        },
    }
    defaults.update(overrides)

    db = TestingSessionLocal()
    try:
        settings = WorkspaceSettings(**defaults)
        db.add(settings)
        db.commit()
        settings_id = settings.id
    finally:
        db.close()
    return settings_id


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

    def test_run_now_returns_202_with_queued_status(self, client):
        """Triggering run-now returns 202 with runId and queued status."""
        ws_id = _create_workspace(client)

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        data = resp.json()
        assert "runId" in data
        assert data["status"] == "queued"
        assert data["message"] == "Pipeline execution queued"

    def test_run_now_creates_run(self, client):
        """Triggering run-now creates a ProcessingRun record (sync via fixture)."""
        ws_id = _create_workspace(client)

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        # Verify the run was created and completed (sync fixture executes it)
        detail_resp = client.get(f"/api/runs/{run_id}")
        assert detail_resp.status_code == 200
        data = detail_resp.json()
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
        """Run-now creates 6 pipeline step events (sync via fixture)."""
        ws_id = _create_workspace(client)

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        # Verify events were created by fetching run detail
        detail_resp = client.get(f"/api/runs/{run_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert len(detail["steps"]) == 6
        step_names = [s["name"] for s in detail["steps"]]
        assert "fetch_feeds" in step_names
        assert "normalize_content" in step_names
        assert "cluster_content" in step_names
        assert "score_content" in step_names
        assert "select_shortlist" in step_names
        assert "generate_report" in step_names

    def test_run_now_completes_successfully(self, client):
        """Run completes with success status and correct affected counts.

        With no feeds in the test DB the pipeline fetches 0 feeds and
        creates 0 articles, but still generates 1 report.
        """
        ws_id = _create_workspace(client)

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        detail_resp = client.get(f"/api/runs/{run_id}")
        data = detail_resp.json()

        assert data["status"] == "success"
        assert data["affectedCounts"]["feeds"] == 0
        assert data["affectedCounts"]["articles"] == 0
        assert data["affectedCounts"]["reports"] == 1

    def test_run_now_all_events_success(self, client):
        """All pipeline events are marked as success/completed after run-now."""
        ws_id = _create_workspace(client)

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        detail_resp = client.get(f"/api/runs/{run_id}")
        assert detail_resp.status_code == 200
        steps = detail_resp.json()["steps"]
        for step in steps:
            assert step["status"] in ("success", "completed")

    def test_run_now_events_have_messages(self, client):
        """Pipeline events have descriptive messages after completion."""
        ws_id = _create_workspace(client)

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        run_id = resp.json()["runId"]

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
        assert resp1.status_code == 202
        assert resp2.status_code == 202
        assert resp1.json()["runId"] != resp2.json()["runId"]

    def test_run_now_appears_in_runs_list(self, client):
        """A run-now run appears in the workspace runs list."""
        ws_id = _create_workspace(client)

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        run_id = resp.json()["runId"]

        list_resp = client.get(f"/api/workspaces/{ws_id}/runs")
        assert list_resp.status_code == 200
        run_ids = [r["id"] for r in list_resp.json()]
        assert run_id in run_ids

    def test_run_now_log_snippets(self, client):
        """Run detail has log snippets from the pipeline events."""
        ws_id = _create_workspace(client)

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        run_id = resp.json()["runId"]

        detail_resp = client.get(f"/api/runs/{run_id}")
        snippets = detail_resp.json()["logSnippets"]
        assert len(snippets) == 6
        assert any("fetch_feeds" in s for s in snippets)

    def test_run_now_links_created_content_items(self, client, monkeypatch):
        """Run detail exposes content item links created during the run."""
        ws_id = _create_workspace(client)
        _create_workspace_profile(client, ws_id, priority_themes=["Fetched", "article"])
        _create_workspace_settings(client, ws_id)
        _create_feed(client, ws_id, url="https://example.com/feed.xml")

        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: FeedFetchResult(
                success=True,
                entries=[
                    {
                        "title": "Fetched article",
                        "url": "https://example.com/article",
                        "source_name": "Example Feed",
                        "published_at": datetime(
                            2024, 3, 20, 8, 0, 0, tzinfo=timezone.utc
                        ),
                        "author": "Author",
                        "summary": "Summary",
                        "content": "Body",
                    }
                ],
                error=None,
                source_title="Example Feed",
            ),
        )

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        detail_resp = client.get(f"/api/runs/{run_id}")
        assert detail_resp.status_code == 200
        content_ids = detail_resp.json()["links"]["contentItems"]
        assert content_ids is not None
        assert isinstance(content_ids, list)
        assert len(content_ids) == 1

    def test_run_now_produces_clustered_content_items(self, client, monkeypatch):
        """After run-now, content items have cluster_id assigned.

        Also verifies that duplicates within the same fetched batch are
        deduplicated at ingestion time (same normalized URL → skip).
        """
        from app.tests.conftest import TestingSessionLocal
        from app.models.content import ContentItem

        ws_id = _create_workspace(client)
        _create_feed(client, ws_id, url="https://example.com/feed.xml")

        # Return two items sharing the same base URL (different tracking params)
        # and one unique item.  The second duplicate should be skipped at
        # ingestion time so only 2 ContentItems are created.
        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: FeedFetchResult(
                success=True,
                entries=[
                    {
                        "title": "Duplicate Story",
                        "url": "https://example.com/story?utm_source=twitter",
                        "source_name": "Example Feed",
                        "published_at": datetime(
                            2024, 3, 20, 8, 0, 0, tzinfo=timezone.utc
                        ),
                        "author": "Author",
                        "summary": "Summary A",
                        "content": "Body A",
                    },
                    {
                        "title": "Duplicate Story",
                        "url": "https://example.com/story?fbclid=abc123",
                        "source_name": "Example Feed",
                        "published_at": datetime(
                            2024, 3, 20, 9, 0, 0, tzinfo=timezone.utc
                        ),
                        "author": "Author",
                        "summary": "Summary B",
                        "content": "Body B",
                    },
                    {
                        "title": "Unique Story",
                        "url": "https://example.com/unique",
                        "source_name": "Example Feed",
                        "published_at": datetime(
                            2024, 3, 20, 10, 0, 0, tzinfo=timezone.utc
                        ),
                        "author": "Author",
                        "summary": "Summary C",
                        "content": "Body C",
                    },
                ],
                error=None,
                source_title="Example Feed",
            ),
        )

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202

        # Query ContentItems directly from the DB
        db = TestingSessionLocal()
        try:
            items = (
                db.query(ContentItem).filter(ContentItem.workspace_id == ws_id).all()
            )
            # The fbclid variant was deduplicated at ingestion time (same
            # normalized URL as the utm_source variant), so only 2 items exist.
            assert len(items) == 2

            # Every item should have a cluster_id
            for item in items:
                assert item.cluster_id is not None, (
                    f"ContentItem {item.id} has no cluster_id"
                )

            # The first duplicate was kept; the fbclid variant was skipped.
            dup_items = [i for i in items if "story?utm" in (i.url or "")]
            dup_fb = [i for i in items if "story?fbclid" in (i.url or "")]
            assert len(dup_items) == 1
            assert len(dup_fb) == 0  # deduplicated at ingestion time

            # The unique item should be in a different cluster
            unique_items = [i for i in items if "/unique" in (i.url or "")]
            assert len(unique_items) == 1
            assert unique_items[0].cluster_id != dup_items[0].cluster_id
        finally:
            db.close()

    def test_run_now_clustering_event_has_metadata(self, client):
        """The cluster_content pipeline event records clusters_created and items_clustered."""
        from app.tests.conftest import TestingSessionLocal
        from app.models.run import ProcessingRunEvent

        ws_id = _create_workspace(client)

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        # Query events directly from the DB
        db = TestingSessionLocal()
        try:
            events = (
                db.query(ProcessingRunEvent)
                .filter(ProcessingRunEvent.run_id == run_id)
                .all()
            )
            cluster_events = [e for e in events if e.step_name == "cluster_content"]
            assert len(cluster_events) == 1

            cluster_event = cluster_events[0]
            assert cluster_event.status == "completed"

            meta = cluster_event.metadata_json
            assert meta is not None
            assert "clusters_created" in meta
            assert "items_clustered" in meta

            # With no feeds configured, expect 0 items clustered
            assert meta["items_clustered"] == 0
            assert meta["clusters_created"] == 0
        finally:
            db.close()

    def test_run_now_clustering_event_with_items(self, client, monkeypatch):
        """Clustering event metadata reflects actual clustered item counts.

        The second duplicate (fbclid variant) is deduplicated at ingestion
        time, so only 2 items reach the clustering step.
        """
        from app.tests.conftest import TestingSessionLocal
        from app.models.run import ProcessingRunEvent

        ws_id = _create_workspace(client)
        _create_feed(client, ws_id, url="https://example.com/feed.xml")

        # Return 3 items: 2 sharing the same base URL (one will be deduped), 1 unique
        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: FeedFetchResult(
                success=True,
                entries=[
                    {
                        "title": "Shared Story",
                        "url": "https://example.com/shared?utm_source=tw",
                        "source_name": "Example Feed",
                        "published_at": datetime(
                            2024, 3, 20, 8, 0, 0, tzinfo=timezone.utc
                        ),
                        "author": "Author",
                        "summary": "Summary",
                        "content": "Body",
                    },
                    {
                        "title": "Shared Story",
                        "url": "https://example.com/shared?fbclid=x",
                        "source_name": "Example Feed",
                        "published_at": datetime(
                            2024, 3, 20, 9, 0, 0, tzinfo=timezone.utc
                        ),
                        "author": "Author",
                        "summary": "Summary",
                        "content": "Body",
                    },
                    {
                        "title": "Solo Story",
                        "url": "https://example.com/solo",
                        "source_name": "Example Feed",
                        "published_at": datetime(
                            2024, 3, 20, 10, 0, 0, tzinfo=timezone.utc
                        ),
                        "author": "Author",
                        "summary": "Summary",
                        "content": "Body",
                    },
                ],
                error=None,
                source_title="Example Feed",
            ),
        )

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        db = TestingSessionLocal()
        try:
            events = (
                db.query(ProcessingRunEvent)
                .filter(ProcessingRunEvent.run_id == run_id)
                .all()
            )
            cluster_events = [e for e in events if e.step_name == "cluster_content"]
            assert len(cluster_events) == 1

            cluster_event = cluster_events[0]
            assert cluster_event.status == "completed"

            meta = cluster_event.metadata_json
            assert meta is not None
            # The fbclid duplicate was deduped at ingestion, so only 2 items
            # reach clustering — both become singletons.
            assert meta["items_clustered"] == 2
            assert meta["clusters_created"] == 2  # 2 singletons
            assert meta["singleton_clusters"] == 2
        finally:
            db.close()


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


# ---------------------------------------------------------------------------
# Scoring integration tests
# ---------------------------------------------------------------------------


class TestRunNowScoring:
    """Integration tests verifying that run-now produces correctly scored content items."""

    def test_run_now_produces_scored_content_items(self, client, monkeypatch):
        """After run-now, content items have score_breakdown_json and final_score set."""
        from app.tests.conftest import TestingSessionLocal
        from app.models.content import ContentItem

        ws_id = _create_workspace(client)
        _create_workspace_profile(client, ws_id)
        _create_workspace_settings(client, ws_id)
        _create_feed(client, ws_id, url="https://example.com/feed.xml")

        now = datetime.now(timezone.utc)
        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: FeedFetchResult(
                success=True,
                entries=[
                    {
                        "title": "AI and machine learning advances in analytics",
                        "url": "https://example.com/article",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=1),
                        "author": "Author",
                        "summary": "AI breakthrough in machine learning analytics",
                        "content": "Body about AI and machine learning analytics",
                    }
                ],
                error=None,
                source_title="Example Feed",
            ),
        )

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202

        db = TestingSessionLocal()
        try:
            items = (
                db.query(ContentItem).filter(ContentItem.workspace_id == ws_id).all()
            )
            assert len(items) == 1

            item = items[0]
            assert item.final_score is not None
            assert item.score_breakdown_json is not None
            breakdown = item.score_breakdown_json

            # Verify breakdown has expected structure
            assert "scores" in breakdown
            assert "weights" in breakdown
            assert "combined_score" in breakdown
            assert "filter_reason" in breakdown

            # Verify individual scores are real (not None, numeric)
            scores = breakdown["scores"]
            for key in (
                "keyword",
                "competitor_mention",
                "freshness",
                "source_authority",
                "bm25",
            ):
                assert key in scores
                assert isinstance(scores[key], (int, float))
        finally:
            db.close()

    def test_included_items_have_scores_above_threshold(self, client, monkeypatch):
        """Items with status='included' have final_score >= min_relevance_score."""
        from app.tests.conftest import TestingSessionLocal
        from app.models.content import ContentItem

        ws_id = _create_workspace(client)
        _create_workspace_profile(client, ws_id)
        _create_workspace_settings(
            client,
            ws_id,
            thresholds={
                "min_relevance_score": 0.1,
                "min_final_score": 0.1,
                "max_articles_per_report": 15,
            },
        )
        _create_feed(client, ws_id, url="https://example.com/feed.xml")

        now = datetime.now(timezone.utc)
        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: FeedFetchResult(
                success=True,
                entries=[
                    {
                        "title": "AI revolutionizes machine learning analytics",
                        "url": "https://example.com/ai-article",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=1),
                        "author": "Author",
                        "summary": "AI breakthrough",
                        "content": "Body about AI and machine learning",
                    },
                    {
                        "title": "CompetitorCorp launches new product",
                        "url": "https://example.com/competitor-article",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=2),
                        "author": "Author",
                        "summary": "CompetitorCorp news",
                        "content": "Body about CompetitorCorp",
                    },
                    {
                        "title": "Generic weather update with no keywords",
                        "url": "https://example.com/weather",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=3),
                        "author": "Author",
                        "summary": "Weather forecast",
                        "content": "Sunny with a chance of rain",
                    },
                ],
                error=None,
                source_title="Example Feed",
            ),
        )

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202

        db = TestingSessionLocal()
        try:
            items = (
                db.query(ContentItem).filter(ContentItem.workspace_id == ws_id).all()
            )
            assert len(items) == 3

            included = [i for i in items if i.status == "included"]
            for item in included:
                assert item.final_score is not None
                assert item.final_score >= 0.1, (
                    f"Included item {item.id} has score {item.final_score} below threshold"
                )
        finally:
            db.close()

    def test_score_breakdown_queryable_via_content_detail_api(
        self, client, monkeypatch
    ):
        """After run-now, the content detail API returns scoreBreakdown with real values."""
        from app.tests.conftest import TestingSessionLocal
        from app.models.content import ContentItem

        ws_id = _create_workspace(client)
        _create_workspace_profile(client, ws_id)
        _create_workspace_settings(client, ws_id)
        _create_feed(client, ws_id, url="https://example.com/feed.xml")

        now = datetime.now(timezone.utc)
        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: FeedFetchResult(
                success=True,
                entries=[
                    {
                        "title": "AI and machine learning in analytics",
                        "url": "https://example.com/article",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=1),
                        "author": "Author",
                        "summary": "AI analytics summary",
                        "content": "Body about AI machine learning analytics",
                    }
                ],
                error=None,
                source_title="Example Feed",
            ),
        )

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202

        # Get the content item ID from the DB
        db = TestingSessionLocal()
        try:
            item = (
                db.query(ContentItem).filter(ContentItem.workspace_id == ws_id).first()
            )
            assert item is not None
            content_id = item.id
        finally:
            db.close()

        # Call the content detail API
        detail_resp = client.get(f"/api/content/{content_id}")
        assert detail_resp.status_code == 200
        data = detail_resp.json()

        # Verify scoreBreakdown is present and has real values
        assert "scoreBreakdown" in data
        sb = data["scoreBreakdown"]
        assert "relevance" in sb
        assert "bm25" in sb
        assert "freshness" in sb
        assert "sourceAuthority" in sb

        # Values should be non-negative floats
        for key in ("relevance", "bm25", "freshness", "sourceAuthority"):
            assert isinstance(sb[key], (int, float))
            assert sb[key] >= 0.0

        # Since the article mentions "AI" and "machine learning" (priority themes),
        # the relevance (keyword) score should be > 0
        assert sb["relevance"] > 0.0

    def test_workspace_thresholds_respected(self, client, monkeypatch):
        """A high min_relevance_score causes more items to be excluded."""
        from app.tests.conftest import TestingSessionLocal
        from app.models.content import ContentItem

        ws_id = _create_workspace(client)
        _create_workspace_profile(client, ws_id)
        # Set a very high threshold — almost nothing should pass
        _create_workspace_settings(
            client,
            ws_id,
            thresholds={
                "min_relevance_score": 0.95,
                "min_final_score": 0.95,
                "max_articles_per_report": 15,
            },
        )
        _create_feed(client, ws_id, url="https://example.com/feed.xml")

        now = datetime.now(timezone.utc)
        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: FeedFetchResult(
                success=True,
                entries=[
                    {
                        "title": "Some generic article",
                        "url": "https://example.com/generic",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=1),
                        "author": "Author",
                        "summary": "A generic article with no keywords",
                        "content": "Generic body text about nothing in particular",
                    },
                    {
                        "title": "AI and machine learning advances",
                        "url": "https://example.com/ai",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=2),
                        "author": "Author",
                        "summary": "AI summary",
                        "content": "Body about AI and machine learning",
                    },
                    {
                        "title": "Another generic article about weather",
                        "url": "https://example.com/weather",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=3),
                        "author": "Author",
                        "summary": "Weather summary",
                        "content": "Sunny weather today",
                    },
                ],
                error=None,
                source_title="Example Feed",
            ),
        )

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202

        db = TestingSessionLocal()
        try:
            items = (
                db.query(ContentItem).filter(ContentItem.workspace_id == ws_id).all()
            )
            assert len(items) == 3

            excluded = [i for i in items if i.status == "excluded"]
            # With a 0.95 threshold, all items should be excluded since
            # maximum possible score is ~0.5 (source_authority=0.5 * 0.15
            # + freshness up to 1.0 * 0.20 + some keyword/bm25 < 0.25 + 0.20)
            assert len(excluded) == 3

            # Verify the exclusion reasons reference the threshold
            reasons = {i.exclusion_reason for i in excluded}
            assert reasons == {"below_relevance_threshold"}
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Shortlist integration tests
# ---------------------------------------------------------------------------


class TestRunNowShortlist:
    """Integration tests verifying that run-now produces a shortlist."""

    def test_run_now_shortlist_event_has_metadata(self, client):
        """The select_shortlist pipeline event records shortlist_size."""
        from app.tests.conftest import TestingSessionLocal
        from app.models.run import ProcessingRunEvent

        ws_id = _create_workspace(client)

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        db = TestingSessionLocal()
        try:
            events = (
                db.query(ProcessingRunEvent)
                .filter(ProcessingRunEvent.run_id == run_id)
                .all()
            )
            shortlist_events = [e for e in events if e.step_name == "select_shortlist"]
            assert len(shortlist_events) == 1

            shortlist_event = shortlist_events[0]
            assert shortlist_event.status == "completed"

            meta = shortlist_event.metadata_json
            assert meta is not None
            assert "shortlist_size" in meta
            assert "included_count" in meta

            # With no feeds configured, expect 0 shortlisted items
            assert meta["shortlist_size"] == 0
            assert meta["included_count"] == 0
        finally:
            db.close()

    def test_run_now_produces_shortlist_of_appropriate_size(self, client, monkeypatch):
        """Run-now produces a shortlist with correct size based on included items."""
        from app.tests.conftest import TestingSessionLocal
        from app.models.run import ProcessingRunEvent

        ws_id = _create_workspace(client)
        _create_workspace_profile(client, ws_id)
        _create_workspace_settings(
            client,
            ws_id,
            thresholds={
                "min_relevance_score": 0.1,
                "min_final_score": 0.1,
                "max_articles_per_report": 10,
            },
        )
        _create_feed(client, ws_id, url="https://example.com/feed.xml")

        now = datetime.now(timezone.utc)
        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: FeedFetchResult(
                success=True,
                entries=[
                    {
                        "title": f"AI article {i}",
                        "url": f"https://example.com/article-{i}",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=i),
                        "author": "Author",
                        "summary": f"AI and machine learning article {i}",
                        "content": f"Body about AI and machine learning {i}",
                    }
                    for i in range(5)
                ],
                error=None,
                source_title="Example Feed",
            ),
        )

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        db = TestingSessionLocal()
        try:
            events = (
                db.query(ProcessingRunEvent)
                .filter(ProcessingRunEvent.run_id == run_id)
                .all()
            )
            shortlist_events = [e for e in events if e.step_name == "select_shortlist"]
            assert len(shortlist_events) == 1

            meta = shortlist_events[0].metadata_json
            assert (
                meta["shortlist_size"] == 5
            )  # All 5 should be included and shortlisted
            assert meta["included_count"] == 5
        finally:
            db.close()

    def test_run_now_shortlist_respects_cluster_dedup(self, client, monkeypatch):
        """Shortlist deduplicates items from the same cluster.

        When duplicates share the same normalized URL within a batch, they
        are deduplicated at ingestion time (only the first is kept), so the
        shortlist step receives fewer items.
        """
        from app.tests.conftest import TestingSessionLocal
        from app.models.run import ProcessingRunEvent

        ws_id = _create_workspace(client)
        _create_workspace_profile(client, ws_id)
        _create_workspace_settings(client, ws_id)
        _create_feed(client, ws_id, url="https://example.com/feed.xml")

        now = datetime.now(timezone.utc)
        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: FeedFetchResult(
                success=True,
                entries=[
                    # Two duplicate stories (same normalized URL)
                    {
                        "title": "Duplicate AI Story",
                        "url": "https://example.com/dup?utm_source=twitter",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=1),
                        "author": "Author",
                        "summary": "AI breakthrough story",
                        "content": "Body about AI breakthrough",
                    },
                    {
                        "title": "Duplicate AI Story",
                        "url": "https://example.com/dup?fbclid=abc123",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=2),
                        "author": "Author",
                        "summary": "AI breakthrough story duplicate",
                        "content": "Body about AI breakthrough duplicate",
                    },
                    # One unique story
                    {
                        "title": "Unique ML Story",
                        "url": "https://example.com/unique-ml",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=3),
                        "author": "Author",
                        "summary": "Machine learning advances",
                        "content": "Body about ML advances",
                    },
                ],
                error=None,
                source_title="Example Feed",
            ),
        )

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        db = TestingSessionLocal()
        try:
            events = (
                db.query(ProcessingRunEvent)
                .filter(ProcessingRunEvent.run_id == run_id)
                .all()
            )
            shortlist_events = [e for e in events if e.step_name == "select_shortlist"]
            assert len(shortlist_events) == 1

            meta = shortlist_events[0].metadata_json
            # The fbclid duplicate was deduped at ingestion time, so only 2
            # items reach the shortlist step.
            assert meta["included_count"] == 2
            # Both items are singletons, so shortlist_size equals included_count.
            assert meta["shortlist_size"] == 2
        finally:
            db.close()

    def test_run_now_llm_failure_causes_run_failure(self, client, monkeypatch):
        """When LLM fails, run is marked failed (endpoint returns 202, check detail)."""
        from app.tests.conftest import TestingSessionLocal
        from app.models.run import ProcessingRunEvent
        from app.services.opencode_client import OpenCodeUnavailableError
        from unittest.mock import MagicMock

        ws_id = _create_workspace(client)
        _create_workspace_profile(client, ws_id)
        _create_workspace_settings(client, ws_id)
        _create_feed(client, ws_id, url="https://example.com/feed.xml")

        now = datetime.now(timezone.utc)
        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: FeedFetchResult(
                success=True,
                entries=[
                    {
                        "title": "AI article",
                        "url": "https://example.com/article",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=1),
                        "author": "Author",
                        "summary": "AI summary",
                        "content": "Body about AI",
                    }
                ],
                error=None,
                source_title="Example Feed",
            ),
        )

        # Mock the client to raise an error
        mock_client = MagicMock()
        mock_client.refine_shortlist.side_effect = OpenCodeUnavailableError(
            "adapter unreachable"
        )
        monkeypatch.setattr(
            "app.services.pipeline.OpenCodeClient",
            lambda **kwargs: mock_client,
        )

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        # Endpoint always returns 202 with queued status (pipeline runs async via fixture)
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        # Verify the run is failed by checking the run detail
        detail_resp = client.get(f"/api/runs/{run_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["status"] == "failed"
        assert "adapter unreachable" in (detail["error"] or "")

        db = TestingSessionLocal()
        try:
            events = (
                db.query(ProcessingRunEvent)
                .filter(ProcessingRunEvent.run_id == run_id)
                .all()
            )
            shortlist_events = [e for e in events if e.step_name == "select_shortlist"]
            assert len(shortlist_events) == 1
            assert shortlist_events[0].status == "error"
            assert "unreachable" in (shortlist_events[0].message or "")
        finally:
            db.close()

    def test_run_now_llm_report_failure_causes_run_failure(self, client, monkeypatch):
        """When LLM fails during report generation, the run is marked failed."""
        from app.tests.conftest import TestingSessionLocal
        from app.models.run import ProcessingRunEvent
        from app.services.opencode_client import OpenCodeUnavailableError
        from unittest.mock import MagicMock

        ws_id = _create_workspace(client)
        _create_workspace_profile(client, ws_id)
        _create_workspace_settings(client, ws_id)
        _create_feed(client, ws_id, url="https://example.com/feed.xml")

        now = datetime.now(timezone.utc)
        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: FeedFetchResult(
                success=True,
                entries=[
                    {
                        "title": "AI article",
                        "url": "https://example.com/article",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=1),
                        "author": "Author",
                        "summary": "AI summary",
                        "content": "Body about AI",
                    }
                ],
                error=None,
                source_title="Example Feed",
            ),
        )

        # Mock the client: shortlist succeeds, report fails
        mock_client = MagicMock()
        mock_client.refine_shortlist.return_value = MagicMock(
            selected_items=[
                {
                    "id": "item-1",
                    "title": "AI article",
                    "score": 0.9,
                    "rationale": "Highly relevant",
                }
            ],
            rationale="Selected 1 item",
        )
        mock_client.generate_report_markdown.side_effect = OpenCodeUnavailableError(
            "report adapter down"
        )
        monkeypatch.setattr(
            "app.services.pipeline.OpenCodeClient",
            lambda **kwargs: mock_client,
        )

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        detail_resp = client.get(f"/api/runs/{run_id}")
        detail = detail_resp.json()
        assert detail["status"] == "failed"
        assert "report adapter down" in (detail["error"] or "")

        db = TestingSessionLocal()
        try:
            events = (
                db.query(ProcessingRunEvent)
                .filter(ProcessingRunEvent.run_id == run_id)
                .all()
            )
            report_events = [e for e in events if e.step_name == "generate_report"]
            assert len(report_events) == 1
            assert report_events[0].status == "error"
            assert "report adapter down" in (report_events[0].message or "")
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Unexpected exception propagation tests
# ---------------------------------------------------------------------------


class TestUnexpectedExceptionPropagation:
    """Verify that unexpected exceptions in critical pipeline steps propagate
    correctly (mark the run as failed, record error events, and do NOT
    silently continue).
    """

    def _setup_workspace_with_content(self, client, monkeypatch):
        """Create workspace with profile, settings, feed, and a fetched article."""
        from app.services.pipeline_steps import FeedFetchResult

        ws_id = _create_workspace(client)
        _create_workspace_profile(client, ws_id)
        _create_workspace_settings(client, ws_id)
        _create_feed(client, ws_id, url="https://example.com/feed.xml")

        now = datetime.now(timezone.utc)
        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: FeedFetchResult(
                success=True,
                entries=[
                    {
                        "title": "AI article",
                        "url": "https://example.com/article",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=1),
                        "author": "Author",
                        "summary": "AI summary",
                        "content": "Body about AI",
                    }
                ],
                error=None,
                source_title="Example Feed",
            ),
        )
        return ws_id

    def test_unexpected_exception_in_scoring_marks_run_failed(
        self, client, monkeypatch
    ):
        """Unexpected RuntimeError in score_content_items marks run as failed."""
        from app.tests.conftest import TestingSessionLocal
        from app.models.run import ProcessingRun, ProcessingRunEvent

        ws_id = self._setup_workspace_with_content(client, monkeypatch)

        # Mock the scoring service to raise an unexpected exception
        monkeypatch.setattr(
            "app.services.pipeline.score_content_items",
            lambda db, items, workspace: (_ for _ in ()).throw(
                RuntimeError("unexpected scoring error")
            ),
        )

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        # Verify run is failed via detail endpoint
        detail_resp = client.get(f"/api/runs/{run_id}")
        detail = detail_resp.json()
        assert detail["status"] == "failed"
        assert "unexpected scoring error" in (detail["error"] or "")

        db = TestingSessionLocal()
        try:
            run = db.query(ProcessingRun).filter(ProcessingRun.id == run_id).first()
            assert run is not None
            assert run.status == "failed"
            assert "unexpected scoring error" in (run.error_summary or "")

            events = (
                db.query(ProcessingRunEvent)
                .filter(ProcessingRunEvent.run_id == run_id)
                .all()
            )
            score_events = [e for e in events if e.step_name == "score_content"]
            assert len(score_events) == 1
            assert score_events[0].status == "error"
            assert "unexpected scoring error" in (score_events[0].message or "")
        finally:
            db.close()

    def test_unexpected_exception_in_shortlist_marks_run_failed(
        self, client, monkeypatch
    ):
        """Unexpected RuntimeError in select_shortlist marks run as failed."""
        from app.tests.conftest import TestingSessionLocal
        from app.models.run import ProcessingRun, ProcessingRunEvent
        from unittest.mock import MagicMock

        ws_id = self._setup_workspace_with_content(client, monkeypatch)

        # Mock the OpenCode client to raise an unexpected exception from shortlist
        mock_client = MagicMock()
        mock_client.refine_shortlist.side_effect = RuntimeError(
            "unexpected shortlist error"
        )
        monkeypatch.setattr(
            "app.services.pipeline.OpenCodeClient",
            lambda **kwargs: mock_client,
        )

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        detail_resp = client.get(f"/api/runs/{run_id}")
        detail = detail_resp.json()
        assert detail["status"] == "failed"
        assert "unexpected shortlist error" in (detail["error"] or "")

        db = TestingSessionLocal()
        try:
            run = db.query(ProcessingRun).filter(ProcessingRun.id == run_id).first()
            assert run is not None
            assert run.status == "failed"
            assert "unexpected shortlist error" in (run.error_summary or "")

            events = (
                db.query(ProcessingRunEvent)
                .filter(ProcessingRunEvent.run_id == run_id)
                .all()
            )
            shortlist_events = [e for e in events if e.step_name == "select_shortlist"]
            assert len(shortlist_events) == 1
            assert shortlist_events[0].status == "error"
            assert "unexpected shortlist error" in (shortlist_events[0].message or "")
        finally:
            db.close()

    def test_unexpected_exception_in_report_generation_marks_run_failed(
        self, client, monkeypatch
    ):
        """Unexpected RuntimeError in generate_report marks run as failed."""
        from app.tests.conftest import TestingSessionLocal
        from app.models.run import ProcessingRun, ProcessingRunEvent
        from unittest.mock import MagicMock

        ws_id = self._setup_workspace_with_content(client, monkeypatch)

        # Mock the OpenCode client: shortlist succeeds, report raises RuntimeError
        mock_client = MagicMock()
        mock_client.refine_shortlist.return_value = MagicMock(
            selected_items=[
                {
                    "id": "item-1",
                    "title": "AI article",
                    "score": 0.9,
                    "rationale": "Highly relevant",
                }
            ],
            rationale="Selected 1 item",
        )
        mock_client.generate_report_markdown.side_effect = RuntimeError(
            "unexpected report error"
        )
        monkeypatch.setattr(
            "app.services.pipeline.OpenCodeClient",
            lambda **kwargs: mock_client,
        )

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        detail_resp = client.get(f"/api/runs/{run_id}")
        detail = detail_resp.json()
        assert detail["status"] == "failed"
        assert "unexpected report error" in (detail["error"] or "")

        db = TestingSessionLocal()
        try:
            run = db.query(ProcessingRun).filter(ProcessingRun.id == run_id).first()
            assert run is not None
            assert run.status == "failed"
            assert "unexpected report error" in (run.error_summary or "")

            events = (
                db.query(ProcessingRunEvent)
                .filter(ProcessingRunEvent.run_id == run_id)
                .all()
            )
            report_events = [e for e in events if e.step_name == "generate_report"]
            assert len(report_events) == 1
            assert report_events[0].status == "error"
            assert "unexpected report error" in (report_events[0].message or "")
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Report generation integration tests
# ---------------------------------------------------------------------------


class TestRunNowReportGeneration:
    """Integration tests verifying that run-now produces real report content."""

    def test_run_now_report_contains_content_titles(self, client, monkeypatch):
        """Report markdown includes actual content item titles (not generic stub)."""
        from app.tests.conftest import TestingSessionLocal
        from app.models.report import ReportMessage

        ws_id = _create_workspace(client)
        _create_workspace_profile(client, ws_id)
        _create_workspace_settings(client, ws_id)
        _create_feed(client, ws_id, url="https://example.com/feed.xml")

        now = datetime.now(timezone.utc)
        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: FeedFetchResult(
                success=True,
                entries=[
                    {
                        "title": "AI breakthrough in healthcare",
                        "url": "https://example.com/ai-health",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=1),
                        "author": "Author",
                        "summary": "AI transforms diagnostics",
                        "content": "Body about AI healthcare",
                    },
                    {
                        "title": "Machine learning trends 2025",
                        "url": "https://example.com/ml-trends",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=2),
                        "author": "Author",
                        "summary": "ML is evolving fast",
                        "content": "Body about ML trends",
                    },
                ],
                error=None,
                source_title="Example Feed",
            ),
        )

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        # Get the report from the run detail links
        detail_resp = client.get(f"/api/runs/{run_id}")
        assert detail_resp.status_code == 200
        report_ids = detail_resp.json()["links"]["reports"]
        assert len(report_ids) == 1

        # Fetch the report messages to get the actual markdown
        msg_resp = client.get(f"/api/report-threads/{report_ids[0]}/messages")
        assert msg_resp.status_code == 200
        messages = msg_resp.json()
        system_msgs = [m for m in messages if m["role"] == "system"]
        assert len(system_msgs) == 1

        report_md = system_msgs[0]["content"]

        # Verify the report contains the actual content item titles
        assert "AI breakthrough in healthcare" in report_md
        assert "Machine learning trends 2025" in report_md

    def test_run_now_report_has_structured_sections(self, client, monkeypatch):
        """Report markdown has structured sections (highlights, source details)."""
        ws_id = _create_workspace(client)
        _create_workspace_profile(client, ws_id)
        _create_workspace_settings(client, ws_id)
        _create_feed(client, ws_id, url="https://example.com/feed.xml")

        now = datetime.now(timezone.utc)
        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: FeedFetchResult(
                success=True,
                entries=[
                    {
                        "title": "AI governance framework",
                        "url": "https://example.com/ai-gov",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=1),
                        "author": "Author",
                        "summary": "New AI regulations",
                        "content": "Body about AI governance",
                    }
                ],
                error=None,
                source_title="Example Feed",
            ),
        )

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        detail_resp = client.get(f"/api/runs/{run_id}")
        report_ids = detail_resp.json()["links"]["reports"]
        assert len(report_ids) == 1

        msg_resp = client.get(f"/api/report-threads/{report_ids[0]}/messages")
        messages = msg_resp.json()
        report_md = [m for m in messages if m["role"] == "system"][0]["content"]

        # Verify the mocked OpenCode output shape rather than the removed
        # deterministic template sections.
        assert "_Generated by OpenCode_" in report_md
        assert "## Executive Brief" in report_md
        assert "## Ranked Source Notes" in report_md
        assert "## Top Highlights" not in report_md
        assert "## Source Details" not in report_md

        # Verify the title/period header exists (title uses customer field)
        assert "# Co — Daily News Digest" in report_md
        assert "Reporting window:" in report_md

    def test_run_now_report_includes_source_links(self, client, monkeypatch):
        """Report markdown contains URLs from the content items."""
        ws_id = _create_workspace(client)
        _create_workspace_profile(client, ws_id)
        _create_workspace_settings(client, ws_id)
        _create_feed(client, ws_id, url="https://example.com/feed.xml")

        now = datetime.now(timezone.utc)
        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: FeedFetchResult(
                success=True,
                entries=[
                    {
                        "title": "AI in finance",
                        "url": "https://finance.example.com/ai-report",
                        "source_name": "Finance Feed",
                        "published_at": now - timedelta(hours=1),
                        "author": "Author",
                        "summary": "AI disrupts banking",
                        "content": "Body about AI in finance",
                    },
                    {
                        "title": "ML in retail",
                        "url": "https://retail.example.com/ml-analysis",
                        "source_name": "Retail Feed",
                        "published_at": now - timedelta(hours=2),
                        "author": "Author",
                        "summary": "ML transforms shopping",
                        "content": "Body about ML in retail",
                    },
                ],
                error=None,
                source_title="Finance Feed",
            ),
        )

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        detail_resp = client.get(f"/api/runs/{run_id}")
        report_ids = detail_resp.json()["links"]["reports"]
        assert len(report_ids) == 1

        msg_resp = client.get(f"/api/report-threads/{report_ids[0]}/messages")
        messages = msg_resp.json()
        report_md = [m for m in messages if m["role"] == "system"][0]["content"]

        # Verify the report contains actual source URLs
        assert "https://finance.example.com/ai-report" in report_md
        assert "https://retail.example.com/ml-analysis" in report_md

    def test_run_now_report_empty_shortlist_has_no_sections(self, client):
        """Report with no content items has no highlights or source details sections."""
        ws_id = _create_workspace(client)

        resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert resp.status_code == 202
        run_id = resp.json()["runId"]

        detail_resp = client.get(f"/api/runs/{run_id}")
        report_ids = detail_resp.json()["links"]["reports"]
        assert len(report_ids) == 1

        msg_resp = client.get(f"/api/report-threads/{report_ids[0]}/messages")
        messages = msg_resp.json()
        report_md = [m for m in messages if m["role"] == "system"][0]["content"]

        # Empty report should not have highlights or source details
        assert "## Top Highlights" not in report_md
        assert "## Source Details" not in report_md
        assert "_Generated by OpenCode_" in report_md
        assert "No source items met the current shortlist criteria." in report_md

    def test_regenerate_creates_new_report_with_workspace_content(
        self, client, monkeypatch
    ):
        """Regenerate endpoint creates a new report with content from workspace items."""
        from unittest.mock import MagicMock
        from app.services.opencode_client import ReportResult
        from app.tests.conftest import TestingSessionLocal
        from app.models.report import Report, ReportMessage

        # Mock the OpenCodeClient used by the regenerate endpoint in
        # app.api.reports so it returns deterministic content that
        # includes the article title.
        _mock_client = MagicMock()
        _mock_client.generate_report_markdown.return_value = ReportResult(
            markdown=(
                "# TestCo — Daily News Digest\n\n"
                "## Top Highlights\n\n"
                "1. Regenerate test article — Article for regenerate test [Read more](https://example.com/regen-test)\n\n"
                "## Source Details\n\n"
                "### Regenerate test article\n\n"
                "Published: 2026-04-10T00:00:00+00:00\n\n"
                "Score: 0.8\n\n"
                "Article for regenerate test\n\n"
                "[Read more](https://example.com/regen-test)"
            ),
            model="test-model",
        )
        monkeypatch.setattr(
            "app.api.reports.OpenCodeClient",
            lambda **kwargs: _mock_client,
        )

        ws_id = _create_workspace(client)
        _create_workspace_profile(client, ws_id)
        _create_workspace_settings(client, ws_id)
        _create_feed(client, ws_id, url="https://example.com/feed.xml")

        now = datetime.now(timezone.utc)
        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: FeedFetchResult(
                success=True,
                entries=[
                    {
                        "title": "Regenerate test article",
                        "url": "https://example.com/regen-test",
                        "source_name": "Example Feed",
                        "published_at": now - timedelta(hours=1),
                        "author": "Author",
                        "summary": "Article for regenerate test",
                        "content": "Body about regenerate test",
                    }
                ],
                error=None,
                source_title="Example Feed",
            ),
        )

        # Create initial report via run-now
        run_resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert run_resp.status_code == 202
        run_id = run_resp.json()["runId"]

        detail_resp = client.get(f"/api/runs/{run_id}")
        report_ids = detail_resp.json()["links"]["reports"]
        assert len(report_ids) == 1
        original_report_id = report_ids[0]

        # Call regenerate endpoint
        regen_resp = client.post(f"/api/reports/{original_report_id}/regenerate")
        assert regen_resp.status_code == 200
        regen_data = regen_resp.json()

        # Verify the regenerated message has content
        assert "content" in regen_data
        assert len(regen_data["content"]) > 0

        # Verify metadata marks it as regenerated
        assert regen_data["metadata"]["regenerated"] is True
        assert regen_data["metadata"]["originalReportId"] == original_report_id

        # Verify the new report contains content from the workspace's items
        assert "Regenerate test article" in regen_data["content"]
        assert "https://example.com/regen-test" in regen_data["content"]

        # Verify regenerate appended content to the same report thread
        db = TestingSessionLocal()
        try:
            all_reports = db.query(Report).filter(Report.workspace_id == ws_id).all()
            assert len(all_reports) == 1
            messages = (
                db.query(ReportMessage)
                .filter(ReportMessage.thread_id == original_report_id)
                .all()
            )
            assert len(messages) == 2  # original + regenerated system messages
        finally:
            db.close()
