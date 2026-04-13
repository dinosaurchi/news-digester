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


class TestRedisSessionStore:
    """Unit tests for the Redis-backed session store (redis_session module)."""

    def test_session_persists_after_creation(self, fake_redis):
        """A session stored via set_session should survive a get_session lookup."""
        from app.services.redis_session import set_session, get_session

        session_id = "test-persist-abc123"
        data = {"user_id": 42, "role": "admin"}

        assert set_session(session_id, data) is True
        retrieved = get_session(session_id)
        assert retrieved == data

    def test_expired_session_returns_none(self, fake_redis):
        """A session with a very short TTL should expire and return None."""
        from app.services.redis_session import set_session, get_session

        session_id = "test-expire-xyz789"
        data = {"user_id": 99}

        # Store with a 1-second TTL
        assert set_session(session_id, data, ttl=1) is True
        retrieved = get_session(session_id)
        assert retrieved == data

        # Advance time past the TTL (fakeredis supports time manipulation)
        fake_redis.expire(f"sme:session:{session_id}", 0)
        # After expiration, the key should be gone
        expired = get_session(session_id)
        assert expired is None

    def test_delete_session_removes_key(self, fake_redis):
        """delete_session should remove the session key from Redis."""
        from app.services.redis_session import set_session, get_session, delete_session

        session_id = "test-delete-123"
        data = {"user_id": 7}

        assert set_session(session_id, data) is True
        assert get_session(session_id) == data

        delete_session(session_id)
        assert get_session(session_id) is None

    def test_clear_sessions_removes_all(self, fake_redis):
        """clear_sessions should remove all sme:session:* keys."""
        from app.services.redis_session import set_session, get_session, clear_sessions

        set_session("sess-a", {"user_id": 1})
        set_session("sess-b", {"user_id": 2})
        set_session("sess-c", {"user_id": 3})

        assert get_session("sess-a") is not None
        assert get_session("sess-b") is not None
        assert get_session("sess-c") is not None

        clear_sessions()

        assert get_session("sess-a") is None
        assert get_session("sess-b") is None
        assert get_session("sess-c") is None

    def test_nonexistent_session_returns_none(self, fake_redis):
        """Getting a session that was never created should return None."""
        from app.services.redis_session import get_session

        assert get_session("does-not-exist") is None

    def test_session_survives_across_multiple_lookups(self, fake_redis):
        """Session data should remain consistent across multiple get calls."""
        from app.services.redis_session import set_session, get_session

        session_id = "test-multi-lookup"
        data = {"user_id": 55, "username": "testuser", "role": "editor"}

        set_session(session_id, data)

        for _ in range(5):
            assert get_session(session_id) == data
