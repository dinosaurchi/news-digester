"""Tests for preference endpoints."""

from app.tests.conftest import TestingSessionLocal


def _create_workspace(client, name="Test WS", customer="Co"):
    resp = client.post("/api/workspaces", json={"name": name, "customer": customer})
    return resp.json()["id"]


class TestPutTopicPreferences:
    """PUT /api/workspaces/{workspace_id}/preferences/topics"""

    def test_put_topic_preferences(self, client):
        """Setting topic preferences returns the created preferences."""
        ws_id = _create_workspace(client)

        resp = client.put(
            f"/api/workspaces/{ws_id}/preferences/topics",
            json={
                "preferences": [
                    {"topic": "AI", "weight": 2.0},
                    {"topic": "Cloud", "weight": 1.5},
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["topic"] == "AI"
        assert data[0]["weight"] == 2.0
        assert "id" in data[0]
        assert data[1]["topic"] == "Cloud"
        assert data[1]["weight"] == 1.5

    def test_put_topic_preferences_replaces(self, client):
        """Subsequent PUT calls replace all existing preferences."""
        ws_id = _create_workspace(client)

        # First set
        client.put(
            f"/api/workspaces/{ws_id}/preferences/topics",
            json={"preferences": [{"topic": "AI", "weight": 2.0}]},
        )

        # Second set — replaces the first
        resp = client.put(
            f"/api/workspaces/{ws_id}/preferences/topics",
            json={
                "preferences": [
                    {"topic": "Security", "weight": 3.0},
                    {"topic": "Edge", "weight": 1.0},
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        topics = [p["topic"] for p in data]
        assert "AI" not in topics
        assert "Security" in topics
        assert "Edge" in topics


class TestPutSourcePreferences:
    """PUT /api/workspaces/{workspace_id}/preferences/sources"""

    def test_put_source_preferences(self, client):
        ws_id = _create_workspace(client)

        resp = client.put(
            f"/api/workspaces/{ws_id}/preferences/sources",
            json={
                "preferences": [
                    {"source": "TechCrunch", "weight": 2.0},
                    {"source": "Ars Technica", "weight": 1.0},
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        sources = [p["source"] for p in data]
        assert "TechCrunch" in sources
        assert "Ars Technica" in sources

    def test_put_source_preferences_replaces(self, client):
        ws_id = _create_workspace(client)

        client.put(
            f"/api/workspaces/{ws_id}/preferences/sources",
            json={"preferences": [{"source": "Old Source", "weight": 1.0}]},
        )

        resp = client.put(
            f"/api/workspaces/{ws_id}/preferences/sources",
            json={"preferences": [{"source": "New Source", "weight": 3.0}]},
        )
        data = resp.json()
        assert len(data) == 1
        assert data[0]["source"] == "New Source"


class TestPutEntityPreferences:
    """PUT /api/workspaces/{workspace_id}/preferences/entities"""

    def test_put_entity_preferences(self, client):
        ws_id = _create_workspace(client)

        resp = client.put(
            f"/api/workspaces/{ws_id}/preferences/entities",
            json={
                "preferences": [
                    {"entity": "CloudGiant", "weight": 2.0},
                    {"entity": "DataNexus", "weight": 1.5},
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        entities = [p["entity"] for p in data]
        assert "CloudGiant" in entities
        assert "DataNexus" in entities


class TestGetPreferencesAfterPut:
    """GET preferences after PUT to verify persistence."""

    def test_get_topic_preferences_after_put(self, client):
        ws_id = _create_workspace(client)

        client.put(
            f"/api/workspaces/{ws_id}/preferences/topics",
            json={
                "preferences": [
                    {"topic": "AI", "weight": 2.0},
                    {"topic": "Cloud", "weight": 1.0},
                ]
            },
        )

        resp = client.get(f"/api/workspaces/{ws_id}/preferences/topics")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        topics = [p["topic"] for p in data]
        assert "AI" in topics
        assert "Cloud" in topics

    def test_get_source_preferences_after_put(self, client):
        ws_id = _create_workspace(client)

        client.put(
            f"/api/workspaces/{ws_id}/preferences/sources",
            json={"preferences": [{"source": "TechCrunch", "weight": 2.0}]},
        )

        resp = client.get(f"/api/workspaces/{ws_id}/preferences/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["source"] == "TechCrunch"

    def test_get_entity_preferences_after_put(self, client):
        ws_id = _create_workspace(client)

        client.put(
            f"/api/workspaces/{ws_id}/preferences/entities",
            json={"preferences": [{"entity": "CloudGiant", "weight": 2.0}]},
        )

        resp = client.get(f"/api/workspaces/{ws_id}/preferences/entities")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["entity"] == "CloudGiant"

    def test_get_empty_preferences(self, client):
        """GET with no preferences returns empty list."""
        ws_id = _create_workspace(client)

        resp = client.get(f"/api/workspaces/{ws_id}/preferences/topics")
        assert resp.status_code == 200
        assert resp.json() == []

        resp = client.get(f"/api/workspaces/{ws_id}/preferences/sources")
        assert resp.status_code == 200
        assert resp.json() == []

        resp = client.get(f"/api/workspaces/{ws_id}/preferences/entities")
        assert resp.status_code == 200
        assert resp.json() == []


class TestPreferenceWorkspace404:
    """All preference endpoints return 404 for nonexistent workspace."""

    def test_put_topic_preferences_workspace_404(self, client):
        resp = client.put(
            "/api/workspaces/nonexistent-id/preferences/topics",
            json={"preferences": [{"topic": "AI", "weight": 1.0}]},
        )
        assert resp.status_code == 404

    def test_put_source_preferences_workspace_404(self, client):
        resp = client.put(
            "/api/workspaces/nonexistent-id/preferences/sources",
            json={"preferences": [{"source": "TC", "weight": 1.0}]},
        )
        assert resp.status_code == 404

    def test_put_entity_preferences_workspace_404(self, client):
        resp = client.put(
            "/api/workspaces/nonexistent-id/preferences/entities",
            json={"preferences": [{"entity": "X", "weight": 1.0}]},
        )
        assert resp.status_code == 404

    def test_get_topic_preferences_workspace_404(self, client):
        resp = client.get("/api/workspaces/nonexistent-id/preferences/topics")
        assert resp.status_code == 404

    def test_get_source_preferences_workspace_404(self, client):
        resp = client.get("/api/workspaces/nonexistent-id/preferences/sources")
        assert resp.status_code == 404

    def test_get_entity_preferences_workspace_404(self, client):
        resp = client.get("/api/workspaces/nonexistent-id/preferences/entities")
        assert resp.status_code == 404
