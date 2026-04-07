"""Tests for /api/workspaces CRUD endpoints."""


class TestListWorkspaces:
    """GET /api/workspaces"""

    def test_list_workspaces_empty(self, client):
        resp = client.get("/api/workspaces")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_workspaces_returns_camel_case(self, client):
        """Verify response keys use camelCase convention."""
        client.post(
            "/api/workspaces",
            json={"name": "Alpha", "customer": "Alpha Corp"},
        )
        resp = client.get("/api/workspaces")
        assert resp.status_code == 200
        ws_list = resp.json()
        assert len(ws_list) == 1

        ws = ws_list[0]
        assert "createdAt" in ws
        assert "updatedAt" in ws
        assert "feedCount" in ws
        assert "lastReportAt" in ws
        assert "nextRunAt" in ws


class TestCreateWorkspace:
    """POST /api/workspaces"""

    def test_create_workspace(self, client):
        resp = client.post(
            "/api/workspaces",
            json={"name": "Test Workspace", "customer": "Test Customer"},
        )
        assert resp.status_code == 201

        data = resp.json()
        assert data["name"] == "Test Workspace"
        assert data["customer"] == "Test Customer"
        assert data["status"] == "active"
        assert "id" in data
        assert "createdAt" in data
        assert "updatedAt" in data
        assert data["feedCount"] == 0

    def test_create_workspace_custom_status(self, client):
        resp = client.post(
            "/api/workspaces",
            json={"name": "Paused WS", "customer": "Co", "status": "paused"},
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "paused"

    def test_create_workspace_validation(self, client):
        """Missing required 'name' field → 422."""
        resp = client.post("/api/workspaces", json={"customer": "Only Customer"})
        assert resp.status_code == 422


class TestGetWorkspace:
    """GET /api/workspaces/{id}"""

    def test_get_workspace(self, client):
        create_resp = client.post(
            "/api/workspaces", json={"name": "Fetch Me", "customer": "Co"}
        )
        ws_id = create_resp.json()["id"]

        resp = client.get(f"/api/workspaces/{ws_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == ws_id
        assert resp.json()["name"] == "Fetch Me"

    def test_get_workspace_not_found(self, client):
        resp = client.get("/api/workspaces/nonexistent-id")
        assert resp.status_code == 404


class TestUpdateWorkspace:
    """PATCH /api/workspaces/{id}"""

    def test_update_workspace(self, client):
        create_resp = client.post(
            "/api/workspaces", json={"name": "Old Name", "customer": "Co"}
        )
        ws_id = create_resp.json()["id"]

        resp = client.patch(f"/api/workspaces/{ws_id}", json={"name": "New Name"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"
        # Other fields should remain unchanged
        assert resp.json()["customer"] == "Co"

    def test_update_workspace_not_found(self, client):
        resp = client.patch("/api/workspaces/nonexistent-id", json={"name": "Nope"})
        assert resp.status_code == 404


class TestDeleteWorkspace:
    """DELETE /api/workspaces/{id} — soft delete"""

    def test_delete_workspace(self, client):
        create_resp = client.post(
            "/api/workspaces", json={"name": "To Delete", "customer": "Co"}
        )
        ws_id = create_resp.json()["id"]

        resp = client.delete(f"/api/workspaces/{ws_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"

        # Subsequent GET must still return the workspace with status "archived"
        resp = client.get(f"/api/workspaces/{ws_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"

    def test_delete_workspace_not_found(self, client):
        resp = client.delete("/api/workspaces/nonexistent-id")
        assert resp.status_code == 404
