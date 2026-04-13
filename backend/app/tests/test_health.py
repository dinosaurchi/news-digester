"""Tests for the health, liveness, and readiness endpoints."""


def test_health(client):
    """GET /api/health returns 200 with {status: 'ok'}."""
    resp = client.get("/api/health")
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "ok"


def test_healthz_liveness(client):
    """GET /api/healthz returns 200 with {status: 'ok'} — no dependency checks."""
    resp = client.get("/api/healthz")
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "ok"


def test_readiness_all_ok(client, monkeypatch):
    """GET /api/ready returns 200 when all dependency checks pass."""
    monkeypatch.setattr("app.main.check_database", lambda: ("ok", None))
    monkeypatch.setattr("app.main.check_redis", lambda: ("ok", None))
    monkeypatch.setattr("app.main.check_opencode", lambda: ("ok", None))

    resp = client.get("/api/ready")
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "ok"
    assert data["checks"] == {
        "database": "ok",
        "redis": "ok",
        "opencode": "ok",
    }
    assert "errors" not in data


def test_readiness_degraded(client, monkeypatch):
    """GET /api/ready returns 503 when a dependency check fails."""
    monkeypatch.setattr("app.main.check_database", lambda: ("ok", None))
    monkeypatch.setattr(
        "app.main.check_redis", lambda: ("failed", "Connection refused")
    )
    monkeypatch.setattr("app.main.check_opencode", lambda: ("ok", None))

    resp = client.get("/api/ready")
    assert resp.status_code == 503

    data = resp.json()
    assert data["status"] == "degraded"
    assert data["checks"] == {
        "database": "ok",
        "redis": "failed",
        "opencode": "ok",
    }
    assert data["errors"] == {
        "redis": "Connection refused",
    }


def test_readiness_multiple_failures(client, monkeypatch):
    """GET /api/ready returns 503 with all failures reported."""
    monkeypatch.setattr(
        "app.main.check_database", lambda: ("failed", "could not connect")
    )
    monkeypatch.setattr(
        "app.main.check_redis", lambda: ("failed", "Connection refused")
    )
    monkeypatch.setattr("app.main.check_opencode", lambda: ("ok", None))

    resp = client.get("/api/ready")
    assert resp.status_code == 503

    data = resp.json()
    assert data["status"] == "degraded"
    assert len(data["errors"]) == 2
    assert "database" in data["errors"]
    assert "redis" in data["errors"]
