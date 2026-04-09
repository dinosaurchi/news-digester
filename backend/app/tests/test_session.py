"""Tests for /api/session/* endpoints."""

from app.models.user import User


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

    def test_login_wrong_password(self, client):
        resp = client.post(
            "/api/session/login",
            json={"username": "admin", "password": "wrong"},
        )
        assert resp.status_code == 401

    def test_login_unknown_user(self, client):
        resp = client.post(
            "/api/session/login",
            json={"username": "unknown", "password": "admin"},
        )
        assert resp.status_code == 401

    def test_login_disabled_user(self, client, db_session):
        user = db_session.query(User).filter(User.username == "admin").one()
        user.status = "disabled"
        db_session.commit()

        resp = client.post(
            "/api/session/login",
            json={"username": "admin", "password": "admin"},
        )
        assert resp.status_code == 401

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


class TestSessionContract:
    """Session response contract consistency tests.

    Verify that /login and /me always return a ``{ user: {...} }`` wrapper
    rather than a flat user object, and that both endpoints produce the
    same user shape.
    """

    def test_login_returns_session_out_with_user_wrapper(self, client):
        resp = client.post(
            "/api/session/login",
            json={"username": "admin", "password": "admin"},
        )
        assert resp.status_code == 200
        data = resp.json()

        # Must have 'user' wrapper key
        assert "user" in data
        user = data["user"]

        # Must have required user fields
        assert "id" in user
        assert "username" in user
        assert "displayName" in user
        assert "role" in user

        # Must NOT be a flat user object — user-level keys must not
        # appear at the top level of the response.
        assert "username" not in data
        assert "displayName" not in data
        assert "role" not in data

    def test_me_returns_session_out_with_user_wrapper(self, client):
        # Login first to establish a session
        login_resp = client.post(
            "/api/session/login",
            json={"username": "admin", "password": "admin"},
        )
        assert login_resp.status_code == 200

        resp = client.get("/api/session/me")
        assert resp.status_code == 200
        data = resp.json()

        # Must have 'user' wrapper key
        assert "user" in data
        user = data["user"]
        assert "id" in user
        assert "username" in user
        assert "displayName" in user
        assert "role" in user

        # Shape should match login's user shape
        login_user = login_resp.json()["user"]
        assert set(user.keys()) == set(login_user.keys())

    def test_me_after_login_returns_same_user_shape(self, client):
        login_resp = client.post(
            "/api/session/login",
            json={"username": "admin", "password": "admin"},
        )
        assert login_resp.status_code == 200

        me_resp = client.get("/api/session/me")
        assert me_resp.status_code == 200

        login_user_keys = set(login_resp.json()["user"].keys())
        me_user_keys = set(me_resp.json()["user"].keys())

        assert login_user_keys == me_user_keys


class TestLogout:
    """POST /api/session/logout"""

    def test_logout(self, auth_client):
        resp = auth_client.post("/api/session/logout")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # After logout, /me must return 401
        resp = auth_client.get("/api/session/me")
        assert resp.status_code == 401
