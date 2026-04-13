"""Tests for feed CRUD endpoints."""

from unittest.mock import MagicMock, patch

import pytest


class TestListFeeds:
    """GET /api/workspaces/{workspace_id}/feeds"""

    def test_list_feeds_empty(self, client):
        """Workspace with no feeds → empty list."""
        # Create a workspace first
        ws_resp = client.post(
            "/api/workspaces", json={"name": "Empty WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]

        resp = client.get(f"/api/workspaces/{ws_id}/feeds")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_feed_workspace_404(self, client):
        """Workspace doesn't exist → 404."""
        resp = client.get("/api/workspaces/nonexistent-id/feeds")
        assert resp.status_code == 404


class TestCreateFeed:
    """POST /api/workspaces/{workspace_id}/feeds"""

    def test_create_feed(self, client):
        """Valid data → 201, returns FeedOut with camelCase."""
        ws_resp = client.post(
            "/api/workspaces", json={"name": "Feed WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]

        resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "TechCrunch",
                "url": "https://techcrunch.com/feed/",
                "type": "rss",
                "cadence": "daily",
                "tags": ["tech"],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "TechCrunch"
        assert data["url"] == "https://techcrunch.com/feed/"
        assert data["type"] == "rss"
        assert data["status"] == "healthy"
        assert data["cadence"] == "daily"
        assert data["tags"] == ["tech"]
        assert "id" in data
        assert "workspaceId" in data
        assert "createdAt" in data
        assert "updatedAt" in data
        assert data["lastFetchedAt"] is None
        assert data["lastError"] is None
        assert data["lastErrorAt"] is None

    def test_create_feed_validation_missing_name(self, client):
        """Missing name → 422."""
        ws_resp = client.post(
            "/api/workspaces", json={"name": "Feed WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]

        resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "url": "https://example.com/feed",
                "type": "rss",
            },
        )
        assert resp.status_code == 422

    def test_create_feed_invalid_type(self, client):
        """Invalid type → 422."""
        ws_resp = client.post(
            "/api/workspaces", json={"name": "Feed WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]

        resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Bad Feed",
                "url": "https://example.com/feed",
                "type": "invalid_type",
            },
        )
        assert resp.status_code == 422

    def test_create_feed_invalid_url(self, client):
        """Invalid URL → 422."""
        ws_resp = client.post(
            "/api/workspaces", json={"name": "Feed WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]

        # Empty URL is invalid
        resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Bad Feed",
                "url": "",
                "type": "rss",
            },
        )
        assert resp.status_code == 422

    def test_create_feed_workspace_404(self, client):
        """Non-existent workspace → 404."""
        resp = client.post(
            "/api/workspaces/nonexistent-id/feeds",
            json={
                "name": "Orphan Feed",
                "url": "https://example.com/feed",
                "type": "rss",
            },
        )
        assert resp.status_code == 404


class TestGetFeed:
    """GET /api/feeds/{feed_id}"""

    def test_get_feed(self, client):
        resp = client.post(
            "/api/workspaces", json={"name": "Feed WS", "customer": "Co"}
        )
        ws_id = resp.json()["id"]

        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "My Feed",
                "url": "https://example.com/feed",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        resp = client.get(f"/api/feeds/{feed_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == feed_id
        assert resp.json()["name"] == "My Feed"

    def test_get_feed_not_found(self, client):
        resp = client.get("/api/feeds/nonexistent-id")
        assert resp.status_code == 404


class TestUpdateFeed:
    """PATCH /api/feeds/{feed_id}"""

    def test_update_feed(self, client):
        resp = client.post(
            "/api/workspaces", json={"name": "Feed WS", "customer": "Co"}
        )
        ws_id = resp.json()["id"]

        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Original Feed",
                "url": "https://example.com/feed",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        resp = client.patch(f"/api/feeds/{feed_id}", json={"name": "Updated Feed"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Feed"
        # Other fields should remain unchanged
        assert resp.json()["url"] == "https://example.com/feed"
        assert resp.json()["type"] == "rss"


class TestDeleteFeed:
    """DELETE /api/feeds/{feed_id}"""

    def test_delete_feed(self, client):
        resp = client.post(
            "/api/workspaces", json={"name": "Feed WS", "customer": "Co"}
        )
        ws_id = resp.json()["id"]

        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "To Delete",
                "url": "https://example.com/feed",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        resp = client.delete(f"/api/feeds/{feed_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == feed_id
        assert resp.json()["status"] == "disabled"

        # Subsequent GET should still return the feed (soft-delete)
        resp = client.get(f"/api/feeds/{feed_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "disabled"

    def test_delete_feed_not_found(self, client):
        resp = client.delete("/api/feeds/nonexistent-id")
        assert resp.status_code == 404


class TestToggleFeed:
    """POST /api/feeds/{feed_id}/toggle"""

    def test_toggle_feed_healthy_to_disabled(self, client):
        resp = client.post(
            "/api/workspaces", json={"name": "Feed WS", "customer": "Co"}
        )
        ws_id = resp.json()["id"]

        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Toggle Feed",
                "url": "https://example.com/feed",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]
        assert create_resp.json()["status"] == "healthy"

        resp = client.post(f"/api/feeds/{feed_id}/toggle")
        assert resp.status_code == 200
        assert resp.json()["status"] == "disabled"

    def test_toggle_feed_disabled_to_healthy(self, client):
        resp = client.post(
            "/api/workspaces", json={"name": "Feed WS", "customer": "Co"}
        )
        ws_id = resp.json()["id"]

        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Toggle Feed",
                "url": "https://example.com/feed",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        # First toggle: healthy → disabled
        client.post(f"/api/feeds/{feed_id}/toggle")

        # Second toggle: disabled → healthy
        resp = client.post(f"/api/feeds/{feed_id}/toggle")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_toggle_feed_error_to_disabled(self, client):
        resp = client.post(
            "/api/workspaces", json={"name": "Feed WS", "customer": "Co"}
        )
        ws_id = resp.json()["id"]

        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Error Feed",
                "url": "https://example.com/feed",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        # Set status to "error" via update
        client.patch(f"/api/feeds/{feed_id}", json={"status": "error"})

        # Toggle: error → disabled
        resp = client.post(f"/api/feeds/{feed_id}/toggle")
        assert resp.status_code == 200
        assert resp.json()["status"] == "disabled"


class TestTestFeed:
    """POST /api/feeds/{feed_id}/test"""

    @patch("app.services.pipeline_steps.httpx.get")
    def test_test_feed(self, mock_get, client):
        response = MagicMock()
        response.text = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Real Test Feed</title>
            <item>
              <title>Article One</title>
              <link>https://example.com/one</link>
              <description>Summary one</description>
            </item>
            <item>
              <title>Article Two</title>
              <link>https://example.com/two</link>
              <description>Summary two</description>
            </item>
          </channel>
        </rss>"""
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        resp = client.post(
            "/api/workspaces", json={"name": "Feed WS", "customer": "Co"}
        )
        ws_id = resp.json()["id"]

        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Test Feed",
                "url": "https://example.com/feed",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        resp = client.post(f"/api/feeds/{feed_id}/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["feedId"] == feed_id
        assert data["message"] == "Feed test completed successfully: parsed 2 articles"
        assert data["articlesFound"] == 2
        assert data["sourceTitle"] == "Real Test Feed"
        assert data["lastFetchedAt"] is not None
        assert data["lastError"] is None

        feed_resp = client.get(f"/api/feeds/{feed_id}")
        feed_data = feed_resp.json()
        assert feed_data["status"] == "healthy"
        assert feed_data["lastFetchedAt"] is not None
        assert feed_data["lastError"] is None
        assert feed_data["lastErrorAt"] is None

    @patch("app.services.pipeline_steps.httpx.get")
    def test_test_feed_parse_error_updates_feed(self, mock_get, client):
        response = MagicMock()
        response.text = "<not-a-feed>"
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        ws_resp = client.post(
            "/api/workspaces", json={"name": "Bad Feed WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]
        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Bad Feed",
                "url": "https://example.com/bad",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        resp = client.post(f"/api/feeds/{feed_id}/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert data["articlesFound"] == 0
        assert data["lastError"]

        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["status"] == "error"
        assert feed_data["lastError"] == data["lastError"]

    @patch("app.services.pipeline_steps.httpx.get")
    def test_test_feed_failure_sets_last_error_at(self, mock_get, client):
        """On failure, last_error_at should be set to a non-null datetime."""
        response = MagicMock()
        response.text = "<not-a-feed>"
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        ws_resp = client.post(
            "/api/workspaces", json={"name": "Bad Feed WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]
        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Bad Feed",
                "url": "https://example.com/bad",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        resp = client.post(f"/api/feeds/{feed_id}/test")
        assert resp.status_code == 200
        assert resp.json()["success"] is False

        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["status"] == "error"
        assert feed_data["lastError"] is not None
        assert feed_data["lastErrorAt"] is not None

    @patch("app.services.pipeline_steps.httpx.get")
    def test_test_feed_failure_does_not_update_last_fetched_at(self, mock_get, client):
        """On failure, last_fetched_at should NOT be updated."""
        # First, succeed to set last_fetched_at to a known value
        success_response = MagicMock()
        success_response.text = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Test Feed</title>
            <item>
              <title>Article One</title>
              <link>https://example.com/one</link>
              <description>Summary one</description>
            </item>
          </channel>
        </rss>"""
        success_response.raise_for_status.return_value = None
        mock_get.return_value = success_response

        ws_resp = client.post(
            "/api/workspaces", json={"name": "Recovery WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]
        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Flip Feed",
                "url": "https://example.com/flip",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        # Successful test sets last_fetched_at
        client.post(f"/api/feeds/{feed_id}/test")
        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        fetched_at_before = feed_data["lastFetchedAt"]
        assert fetched_at_before is not None

        # Now fail — last_fetched_at must not change
        fail_response = MagicMock()
        fail_response.text = "<not-a-feed>"
        fail_response.raise_for_status.return_value = None
        mock_get.return_value = fail_response

        client.post(f"/api/feeds/{feed_id}/test")
        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["status"] == "error"
        assert feed_data["lastFetchedAt"] == fetched_at_before

    @patch("app.services.pipeline_steps.httpx.get")
    def test_test_feed_success_clears_error_state(self, mock_get, client):
        """Success after error clears last_error, last_error_at, sets healthy."""
        # First, fail to put feed into error state
        fail_response = MagicMock()
        fail_response.text = "<not-a-feed>"
        fail_response.raise_for_status.return_value = None
        mock_get.return_value = fail_response

        ws_resp = client.post(
            "/api/workspaces", json={"name": "Recovery WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]
        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Recovery Feed",
                "url": "https://example.com/recovery",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        client.post(f"/api/feeds/{feed_id}/test")
        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["status"] == "error"
        assert feed_data["lastError"] is not None
        assert feed_data["lastErrorAt"] is not None

        # Now succeed — error state should be cleared
        success_response = MagicMock()
        success_response.text = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Recovered Feed</title>
            <item>
              <title>Article One</title>
              <link>https://example.com/one</link>
              <description>Summary one</description>
            </item>
          </channel>
        </rss>"""
        success_response.raise_for_status.return_value = None
        mock_get.return_value = success_response

        resp = client.post(f"/api/feeds/{feed_id}/test")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["status"] == "healthy"
        assert feed_data["lastError"] is None
        assert feed_data["lastErrorAt"] is None

    @patch("app.services.pipeline_steps.httpx.get")
    def test_test_feed_success_updates_last_fetched_at(self, mock_get, client):
        """On success, last_fetched_at should be set to a non-null datetime."""
        response = MagicMock()
        response.text = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Fetch Test Feed</title>
            <item>
              <title>Article One</title>
              <link>https://example.com/one</link>
              <description>Summary one</description>
            </item>
          </channel>
        </rss>"""
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        ws_resp = client.post(
            "/api/workspaces", json={"name": "Fetch WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]
        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Fetch Feed",
                "url": "https://example.com/fetch",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        # Confirm last_fetched_at is None before test
        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["lastFetchedAt"] is None

        resp = client.post(f"/api/feeds/{feed_id}/test")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert resp.json()["lastFetchedAt"] is not None

        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["lastFetchedAt"] is not None

    @patch("app.services.pipeline_steps.httpx.get")
    def test_test_feed_recovery_then_failure(self, mock_get, client):
        """Success then failure: feed goes healthy, then back to error."""
        ws_resp = client.post(
            "/api/workspaces", json={"name": "Flip WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]
        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Flip Feed",
                "url": "https://example.com/flip",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        # Step 1: succeed
        success_response = MagicMock()
        success_response.text = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Flip Feed</title>
            <item>
              <title>Article One</title>
              <link>https://example.com/one</link>
              <description>Summary one</description>
            </item>
          </channel>
        </rss>"""
        success_response.raise_for_status.return_value = None
        mock_get.return_value = success_response

        client.post(f"/api/feeds/{feed_id}/test")
        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["status"] == "healthy"
        assert feed_data["lastError"] is None
        assert feed_data["lastErrorAt"] is None
        fetched_at_after_success = feed_data["lastFetchedAt"]
        assert fetched_at_after_success is not None

        # Step 2: fail — feed goes back to error, last_fetched_at unchanged
        fail_response = MagicMock()
        fail_response.text = "<not-a-feed>"
        fail_response.raise_for_status.return_value = None
        mock_get.return_value = fail_response

        resp = client.post(f"/api/feeds/{feed_id}/test")
        assert resp.status_code == 200
        assert resp.json()["success"] is False

        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["status"] == "error"
        assert feed_data["lastError"] is not None
        assert feed_data["lastErrorAt"] is not None
        assert feed_data["lastFetchedAt"] == fetched_at_after_success


class TestFeedCountInWorkspace:
    """Verify workspace feedCount reflects actual feeds."""

    def test_feed_count_in_workspace(self, client):
        # Create workspace
        ws_resp = client.post(
            "/api/workspaces", json={"name": "Count WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]
        assert ws_resp.json()["feedCount"] == 0

        # Create 3 feeds
        for i in range(3):
            client.post(
                f"/api/workspaces/{ws_id}/feeds",
                json={
                    "name": f"Feed {i}",
                    "url": f"https://example.com/feed{i}",
                    "type": "rss",
                },
            )

        # Check workspace feed count
        resp = client.get(f"/api/workspaces/{ws_id}")
        assert resp.status_code == 200
        assert resp.json()["feedCount"] == 3


class TestFeedReliabilityTracking:
    """Feed reliability tracking: fetch counts, success rates, stale detection."""

    def test_new_feed_has_zero_fetch_counts(self, client):
        """A newly created feed starts with zero fetch counters."""
        ws_resp = client.post(
            "/api/workspaces", json={"name": "Reliability WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]

        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={"name": "New Feed", "url": "https://example.com/feed", "type": "rss"},
        )
        feed_id = create_resp.json()["id"]

        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["totalFetchCount"] == 0
        assert feed_data["consecutiveFetchFailures"] == 0
        assert feed_data["fetchSuccessRate"] == 0.0
        assert feed_data["isStale"] is False

    @patch("app.services.pipeline_steps.httpx.get")
    def test_successful_fetch_increments_total_and_resets_failures(
        self, mock_get, client
    ):
        """A successful fetch test increments total_fetch_count and resets failures."""
        response = MagicMock()
        response.text = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Test Feed</title>
            <item>
              <title>Article One</title>
              <link>https://example.com/one</link>
              <description>Summary one</description>
            </item>
          </channel>
        </rss>"""
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        ws_resp = client.post(
            "/api/workspaces", json={"name": "Fetch Track WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]
        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Track Feed",
                "url": "https://example.com/track",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        # First successful fetch
        client.post(f"/api/feeds/{feed_id}/test")
        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["totalFetchCount"] == 1
        assert feed_data["consecutiveFetchFailures"] == 0
        assert feed_data["fetchSuccessRate"] == pytest.approx(1.0)
        assert feed_data["isStale"] is False

        # Second successful fetch
        client.post(f"/api/feeds/{feed_id}/test")
        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["totalFetchCount"] == 2
        assert feed_data["consecutiveFetchFailures"] == 0
        assert feed_data["fetchSuccessRate"] == pytest.approx(1.0)

    @patch("app.services.pipeline_steps.httpx.get")
    def test_failed_fetch_increments_consecutive_failures(self, mock_get, client):
        """A failed fetch test increments consecutive failures."""
        fail_response = MagicMock()
        fail_response.text = "<not-a-feed>"
        fail_response.raise_for_status.return_value = None
        mock_get.return_value = fail_response

        ws_resp = client.post(
            "/api/workspaces", json={"name": "Fail Track WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]
        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Fail Feed",
                "url": "https://example.com/fail",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        # First failure
        client.post(f"/api/feeds/{feed_id}/test")
        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["totalFetchCount"] == 1
        assert feed_data["consecutiveFetchFailures"] == 1

        # Second failure
        client.post(f"/api/feeds/{feed_id}/test")
        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["totalFetchCount"] == 2
        assert feed_data["consecutiveFetchFailures"] == 2

    @patch("app.services.pipeline_steps.httpx.get")
    def test_success_resets_consecutive_failures(self, mock_get, client):
        """After failures, a success resets consecutive_fetch_failures to 0."""
        fail_response = MagicMock()
        fail_response.text = "<not-a-feed>"
        fail_response.raise_for_status.return_value = None
        mock_get.return_value = fail_response

        ws_resp = client.post(
            "/api/workspaces", json={"name": "Reset WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]
        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Reset Feed",
                "url": "https://example.com/reset",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        # 3 failures
        for _ in range(3):
            client.post(f"/api/feeds/{feed_id}/test")
        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["consecutiveFetchFailures"] == 3
        assert feed_data["totalFetchCount"] == 3

        # Now succeed
        success_response = MagicMock()
        success_response.text = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel><title>OK</title>
            <item><title>A</title><link>https://example.com/a</link></item>
          </channel>
        </rss>"""
        success_response.raise_for_status.return_value = None
        mock_get.return_value = success_response

        client.post(f"/api/feeds/{feed_id}/test")
        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["consecutiveFetchFailures"] == 0
        assert feed_data["totalFetchCount"] == 4

    @patch("app.services.pipeline_steps.httpx.get")
    def test_feed_not_stale_below_threshold(self, mock_get, client):
        """A feed is not stale until consecutive failures reach the threshold."""
        fail_response = MagicMock()
        fail_response.text = "<not-a-feed>"
        fail_response.raise_for_status.return_value = None
        mock_get.return_value = fail_response

        ws_resp = client.post(
            "/api/workspaces", json={"name": "Stale WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]
        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Stale Feed",
                "url": "https://example.com/stale",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        # 4 failures (below default threshold of 5)
        for _ in range(4):
            client.post(f"/api/feeds/{feed_id}/test")
        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["isStale"] is False

    @patch("app.services.pipeline_steps.httpx.get")
    def test_feed_stale_at_threshold(self, mock_get, client):
        """A feed becomes stale when consecutive failures >= threshold (default 5)."""
        fail_response = MagicMock()
        fail_response.text = "<not-a-feed>"
        fail_response.raise_for_status.return_value = None
        mock_get.return_value = fail_response

        ws_resp = client.post(
            "/api/workspaces", json={"name": "Stale At WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]
        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Stale At Feed",
                "url": "https://example.com/stale-at",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        # 5 consecutive failures → stale
        for _ in range(5):
            client.post(f"/api/feeds/{feed_id}/test")
        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["isStale"] is True
        assert feed_data["consecutiveFetchFailures"] == 5
        assert feed_data["totalFetchCount"] == 5

    @patch("app.services.pipeline_steps.httpx.get")
    def test_stale_flag_cleared_on_success(self, mock_get, client):
        """A successful fetch clears the stale flag."""
        fail_response = MagicMock()
        fail_response.text = "<not-a-feed>"
        fail_response.raise_for_status.return_value = None
        mock_get.return_value = fail_response

        ws_resp = client.post(
            "/api/workspaces", json={"name": "Clear Stale WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]
        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Clear Stale Feed",
                "url": "https://example.com/clear-stale",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        # 5 failures → stale
        for _ in range(5):
            client.post(f"/api/feeds/{feed_id}/test")
        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["isStale"] is True

        # Now succeed → stale cleared
        success_response = MagicMock()
        success_response.text = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel><title>OK</title>
            <item><title>A</title><link>https://example.com/a</link></item>
          </channel>
        </rss>"""
        success_response.raise_for_status.return_value = None
        mock_get.return_value = success_response

        client.post(f"/api/feeds/{feed_id}/test")
        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert feed_data["isStale"] is False
        assert feed_data["consecutiveFetchFailures"] == 0

    def test_feed_detail_includes_reliability_fields(self, client):
        """Feed detail response includes all reliability fields."""
        ws_resp = client.post(
            "/api/workspaces", json={"name": "Detail WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]
        create_resp = client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "Detail Feed",
                "url": "https://example.com/detail",
                "type": "rss",
            },
        )
        feed_id = create_resp.json()["id"]

        feed_data = client.get(f"/api/feeds/{feed_id}").json()
        assert "isStale" in feed_data
        assert "fetchSuccessRate" in feed_data
        assert "consecutiveFetchFailures" in feed_data
        assert "totalFetchCount" in feed_data

    def test_feed_list_includes_reliability_fields(self, client):
        """Feed list response includes all reliability fields."""
        ws_resp = client.post(
            "/api/workspaces", json={"name": "List Rel WS", "customer": "Co"}
        )
        ws_id = ws_resp.json()["id"]
        client.post(
            f"/api/workspaces/{ws_id}/feeds",
            json={
                "name": "List Feed",
                "url": "https://example.com/list",
                "type": "rss",
            },
        )

        feeds = client.get(f"/api/workspaces/{ws_id}/feeds").json()
        assert len(feeds) == 1
        feed = feeds[0]
        assert "isStale" in feed
        assert "fetchSuccessRate" in feed
        assert "consecutiveFetchFailures" in feed
        assert "totalFetchCount" in feed
