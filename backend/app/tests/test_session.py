"""Tests for /api/session/* endpoints."""


class TestLogin:
    """POST /api/session/login"""

    def test_login_success(self, client):
        resp = client.post(
            "/api/session/login",
            json={"username": "admin", "password": "admin"},
        )
        assert resp.status_code == 200

        data = resp.json()
        assert "user" in data
        user = data["user"]
        assert user["username"] == "admin"
        assert "id" in user
        assert "displayName" in user
        assert user["role"] == "admin"

    def test_login_empty_credentials(self, client):
        resp = client.post("/api/session/login", json={"username": "", "password": ""})
        assert resp.status_code == 422

    def test_login_whitespace_credentials(self, client):
        """Whitespace-only credentials should be rejected (422)."""
        resp = client.post(
            "/api/session/login", json={"username": "   ", "password": "   "}
        )
        assert resp.status_code == 422

    def test_login_missing_body(self, client):
        """Missing required fields triggers Pydantic validation (422)."""
        resp = client.post("/api/session/login", json={})
        assert resp.status_code == 422


class TestMe:
    """GET /api/session/me"""

    def test_me_authenticated(self, auth_client):
        resp = auth_client.get("/api/session/me")
        assert resp.status_code == 200

        data = resp.json()
        assert "user" in data
        user = data["user"]
        assert "displayName" in user
        assert "id" in user
        assert "role" in user

    def test_me_unauthenticated(self, client):
        resp = client.get("/api/session/me")
        assert resp.status_code == 401


class TestLogout:
    """POST /api/session/logout"""

    def test_logout(self, auth_client):
        resp = auth_client.post("/api/session/logout")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # After logout, /me must return 401
        resp = auth_client.get("/api/session/me")
        assert resp.status_code == 401
