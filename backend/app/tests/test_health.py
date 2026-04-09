"""Tests for the health endpoint."""


def test_health(client):
    """GET /api/health returns 200 with {status: 'ok'}."""
    resp = client.get("/api/health")
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "ok"
