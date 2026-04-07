"""Tests for /api/workspaces/{id}/profile endpoints."""


def _create_workspace(client):
    """Helper: create a workspace and return its ID."""
    resp = client.post("/api/workspaces", json={"name": "Profile WS", "customer": "Co"})
    return resp.json()["id"]


class TestGetProfile:
    """GET /api/workspaces/{id}/profile"""

    def test_get_profile_creates_default(self, client):
        ws_id = _create_workspace(client)

        resp = client.get(f"/api/workspaces/{ws_id}/profile")
        assert resp.status_code == 200

        data = resp.json()
        assert data["workspaceId"] == ws_id
        assert data["businessName"] == ""
        assert data["description"] == ""
        assert data["products"] == []
        assert data["competitors"] == []
        assert data["priorityThemes"] == []
        assert data["excludedTopics"] == []
        assert data["notes"] == ""
        assert "updatedAt" in data

    def test_get_profile_returns_camel_case(self, client):
        ws_id = _create_workspace(client)

        resp = client.get(f"/api/workspaces/{ws_id}/profile")
        data = resp.json()

        # Verify all expected camelCase keys are present
        expected_keys = [
            "id",
            "workspaceId",
            "businessName",
            "description",
            "products",
            "competitors",
            "priorityThemes",
            "excludedTopics",
            "notes",
            "updatedAt",
        ]
        for key in expected_keys:
            assert key in data, f"Missing camelCase key: {key}"


class TestPutProfile:
    """PUT /api/workspaces/{id}/profile"""

    def test_put_profile(self, client):
        ws_id = _create_workspace(client)

        payload = {
            "businessName": "Acme Corp",
            "description": "A worldwide leader in widgets.",
            "products": ["Widget Pro", "Widget Lite"],
            "competitors": ["Globex", "Initech"],
            "priorityThemes": ["AI", "Supply Chain"],
            "excludedTopics": ["Sports", "Entertainment"],
            "notes": "Focus on B2B trends.",
        }

        resp = client.put(f"/api/workspaces/{ws_id}/profile", json=payload)
        assert resp.status_code == 200

        data = resp.json()
        assert data["businessName"] == "Acme Corp"
        assert data["description"] == "A worldwide leader in widgets."
        assert data["products"] == ["Widget Pro", "Widget Lite"]
        assert data["competitors"] == ["Globex", "Initech"]
        assert data["priorityThemes"] == ["AI", "Supply Chain"]
        assert data["excludedTopics"] == ["Sports", "Entertainment"]
        assert data["notes"] == "Focus on B2B trends."

    def test_put_profile_partial_update(self, client):
        """Sending only some fields updates those and resets list fields to defaults.

        NOTE: The Pydantic input model provides default values (empty lists)
        for omitted list fields, and the service applies all non-None values.
        So a partial PUT resets list fields to ``[]``.
        """
        ws_id = _create_workspace(client)

        # First, set all fields
        full_payload = {
            "businessName": "Original Name",
            "description": "Original desc",
            "products": ["P1"],
            "competitors": ["C1"],
            "priorityThemes": ["T1"],
            "excludedTopics": ["E1"],
            "notes": "Original notes",
        }
        client.put(f"/api/workspaces/{ws_id}/profile", json=full_payload)

        # Now update only businessName — list fields reset to defaults
        resp = client.put(
            f"/api/workspaces/{ws_id}/profile",
            json={"businessName": "Updated Name"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["businessName"] == "Updated Name"
        # List fields are reset to their Pydantic defaults (empty lists)
        assert data["products"] == []
        assert data["competitors"] == []
        # String fields that were not sent remain as None → service skips them
        assert data["description"] == "Original desc"
        assert data["notes"] == "Original notes"

    def test_put_profile_validation(self, client):
        """businessName too short (< 2 chars) → 422."""
        ws_id = _create_workspace(client)

        resp = client.put(
            f"/api/workspaces/{ws_id}/profile",
            json={"businessName": "A"},
        )
        assert resp.status_code == 422

    def test_put_profile_not_found(self, client):
        resp = client.put(
            "/api/workspaces/nonexistent-id/profile",
            json={"businessName": "Nope"},
        )
        assert resp.status_code == 404
