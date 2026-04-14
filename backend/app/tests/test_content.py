"""Tests for content API endpoints."""

from datetime import datetime, timezone


def _create_workspace(client):
    """Helper to create a workspace and return its ID."""
    resp = client.post("/api/workspaces", json={"name": "Content WS", "customer": "Co"})
    return resp.json()["id"]


def _create_content_item(client, workspace_id, **overrides):
    """Helper to create a content item via direct DB insert through the API.
    Since we don't have a POST endpoint, we'll use the DB session directly.
    """
    # We need to insert via the test client's overridden DB session
    # Use the conftest db_session fixture pattern - but since we're in a test
    # without access to that fixture, we'll use the API to seed data via
    # a different approach: import models and use TestingSessionLocal
    from app.tests.conftest import TestingSessionLocal
    from app.models.content import ContentItem

    defaults = {
        "id": overrides.pop("id", None),
        "workspace_id": workspace_id,
        "title": "Test Content Item",
        "content_type": "news",
        "status": "pending",
        "local_relevance_score": 0.8,
        "llm_score": 0.7,
        "final_score": 0.75,
        "published_at": datetime(2024, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
    }
    defaults.update(overrides)

    db = TestingSessionLocal()
    try:
        item = ContentItem(**defaults)
        db.add(item)
        db.commit()
        item_id = item.id
    finally:
        db.close()
    return item_id


class TestListContent:
    """GET /api/workspaces/{workspace_id}/content"""

    def test_list_content_empty(self, client):
        """Workspace with no content items → empty list."""
        ws_id = _create_workspace(client)

        resp = client.get(f"/api/workspaces/{ws_id}/content")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_content_with_data(self, client):
        """Workspace with content items → returns list."""
        ws_id = _create_workspace(client)
        _create_content_item(client, ws_id, title="Item 1")
        _create_content_item(client, ws_id, title="Item 2")

        resp = client.get(f"/api/workspaces/{ws_id}/content")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        titles = [item["title"] for item in data]
        assert "Item 1" in titles
        assert "Item 2" in titles

    def test_list_content_uses_bm25_for_legacy_llm_score_field(self, client):
        """List API exposes persisted BM25 when llm_score is unset."""
        ws_id = _create_workspace(client)
        _create_content_item(
            client,
            ws_id,
            title="BM25-backed item",
            llm_score=None,
            score_breakdown_json={
                "scores": {
                    "keyword": 0.4,
                    "bm25": 0.61,
                    "freshness": 0.8,
                    "source_authority": 0.5,
                },
                "weights": {"keyword": 0.25, "bm25": 0.2},
            },
        )

        resp = client.get(f"/api/workspaces/{ws_id}/content")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["llmScore"] == 0.61

    def test_list_content_filter_status(self, client):
        """Filter by status returns only matching items."""
        ws_id = _create_workspace(client)
        _create_content_item(client, ws_id, title="Included", status="included")
        _create_content_item(client, ws_id, title="Excluded", status="excluded")
        _create_content_item(client, ws_id, title="Pending", status="pending")

        resp = client.get(f"/api/workspaces/{ws_id}/content?status=included")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Included"
        assert data[0]["status"] == "included"

    def test_list_content_filter_type(self, client):
        """Filter by type returns only matching items."""
        ws_id = _create_workspace(client)
        _create_content_item(client, ws_id, title="News", content_type="news")
        _create_content_item(client, ws_id, title="Blog", content_type="blog")

        resp = client.get(f"/api/workspaces/{ws_id}/content?type=blog")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Blog"
        assert data[0]["type"] == "blog"

    def test_list_content_filter_min_score(self, client):
        """Filter by minScore returns only items with score >= threshold."""
        ws_id = _create_workspace(client)
        _create_content_item(client, ws_id, title="High Score", final_score=0.9)
        _create_content_item(client, ws_id, title="Low Score", final_score=0.3)

        resp = client.get(f"/api/workspaces/{ws_id}/content?minScore=0.5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "High Score"

    def test_list_content_filter_date_range(self, client):
        """Filter by dateFrom and dateTo returns items in range."""
        ws_id = _create_workspace(client)
        _create_content_item(
            client,
            ws_id,
            title="Old",
            published_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        )
        _create_content_item(
            client,
            ws_id,
            title="New",
            published_at=datetime(2024, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
        )

        resp = client.get(
            f"/api/workspaces/{ws_id}/content"
            f"?dateFrom=2024-03-01T00:00:00Z"
            f"&dateTo=2024-03-31T23:59:59Z"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "New"

    def test_list_content_filter_source(self, client):
        """Filter by source returns only items from that source."""
        ws_id = _create_workspace(client)
        _create_content_item(client, ws_id, title="TC", source_name="TechCrunch")
        _create_content_item(client, ws_id, title="Verge", source_name="The Verge")

        resp = client.get(f"/api/workspaces/{ws_id}/content?source=TechCrunch")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["source"] == "TechCrunch"

    def test_content_workspace_404(self, client):
        """Workspace doesn't exist → 404."""
        resp = client.get("/api/workspaces/nonexistent-id/content")
        assert resp.status_code == 404


class TestGetContentDetail:
    """GET /api/content/{content_item_id}"""

    def test_get_content_detail(self, client):
        """Returns content item with scoreBreakdown."""
        ws_id = _create_workspace(client)
        item_id = _create_content_item(
            client,
            ws_id,
            title="Detail Test",
            raw_text="Full body text here",
            local_relevance_score=0.85,
            llm_score=0.9,
            final_score=0.87,
        )

        resp = client.get(f"/api/content/{item_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == item_id
        assert data["title"] == "Detail Test"
        assert "scoreBreakdown" in data
        assert data["scoreBreakdown"]["relevance"] == 0.85
        assert data["scoreBreakdown"]["llm"] == 0.9
        assert "freshness" in data["scoreBreakdown"]
        assert "sourceAuthority" in data["scoreBreakdown"]

    def test_get_content_detail_uses_bm25_for_legacy_llm_breakdown_field(self, client):
        """Detail API maps persisted BM25 into the legacy llm breakdown field."""
        ws_id = _create_workspace(client)
        item_id = _create_content_item(
            client,
            ws_id,
            title="BM25 detail test",
            llm_score=None,
            score_breakdown_json={
                "scores": {
                    "keyword": 0.5,
                    "bm25": 0.72,
                    "freshness": 0.9,
                    "source_authority": 0.4,
                },
                "weights": {"keyword": 0.25, "bm25": 0.2},
            },
        )

        resp = client.get(f"/api/content/{item_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["llmScore"] == 0.72
        assert data["scoreBreakdown"]["llm"] == 0.72

    def test_get_content_detail_with_cluster(self, client):
        """Content item with cluster_id returns clusterItems."""
        ws_id = _create_workspace(client)
        cluster_id = "cluster-abc"
        item_id = _create_content_item(
            client,
            ws_id,
            title="Cluster Main",
            cluster_id=cluster_id,
        )
        _create_content_item(
            client,
            ws_id,
            title="Cluster Sibling",
            cluster_id=cluster_id,
        )

        resp = client.get(f"/api/content/{item_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "clusterItems" in data
        assert len(data["clusterItems"]) == 1
        assert data["clusterItems"][0]["title"] == "Cluster Sibling"

    def test_get_content_not_found(self, client):
        """Non-existent content item → 404."""
        resp = client.get("/api/content/nonexistent-id")
        assert resp.status_code == 404

    def test_content_camel_case(self, client):
        """Response uses camelCase keys matching frontend contract."""
        ws_id = _create_workspace(client)
        _create_content_item(
            client,
            ws_id,
            title="CamelCase Test",
            source_name="TechCrunch",
            url="https://example.com/article",
            content_type="news",
            local_relevance_score=0.8,
            llm_score=0.7,
            final_score=0.75,
        )

        resp = client.get(f"/api/workspaces/{ws_id}/content")
        assert resp.status_code == 200
        data = resp.json()[0]
        # Verify camelCase keys
        assert "workspaceId" in data
        assert "sourceUrl" in data
        assert "publishedAt" in data
        assert "relevanceScore" in data
        assert "llmScore" in data
        assert "finalScore" in data
        assert "clusterId" in data
        assert "inclusionReason" in data
        assert "exclusionReason" in data
        assert "linkedReportIds" in data


class TestDeleteContentItem:
    """DELETE /api/content/{content_item_id}"""

    def test_delete_content_item_success(self, auth_client):
        """Authenticated delete of existing item returns 204."""
        ws_id = _create_workspace(auth_client)
        item_id = _create_content_item(auth_client, ws_id, title="To Delete")

        resp = auth_client.delete(f"/api/content/{item_id}")
        assert resp.status_code == 204

    def test_delete_content_item_gone_from_db(self, auth_client):
        """After delete, the item no longer exists in the database."""
        ws_id = _create_workspace(auth_client)
        item_id = _create_content_item(auth_client, ws_id, title="Gone")

        auth_client.delete(f"/api/content/{item_id}")

        resp = auth_client.get(f"/api/content/{item_id}")
        assert resp.status_code == 404

    def test_delete_content_item_not_found(self, auth_client):
        """Deleting a non-existent item returns 404."""
        resp = auth_client.delete("/api/content/nonexistent-id")
        assert resp.status_code == 404

    def test_delete_content_item_unauthenticated(self, client):
        """Delete without authentication returns 401."""
        ws_id = _create_workspace(client)
        item_id = _create_content_item(client, ws_id, title="Protected")

        resp = client.delete(f"/api/content/{item_id}")
        assert resp.status_code == 401
