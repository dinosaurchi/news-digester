"""Tests for feed CRUD endpoints."""

from unittest.mock import MagicMock, patch


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
