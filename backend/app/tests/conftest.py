"""Shared test fixtures for the backend API tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.workspace import (  # noqa: F401 — ensure models are registered with Base
    Workspace,
    WorkspaceProfile,
    WorkspaceSettings,
)
from app.models.feed import FeedSource  # noqa: F401 — ensure model is registered with Base
from app.models.report import (  # noqa: F401 — ensure models are registered with Base
    Report,
    ReportMessage,
    FeedbackEvent,
)
from app.main import app
from app.db.session import get_db

# ── SQLite in-memory database for testing ─────────────────────────────
# StaticPool keeps a single connection that is shared across threads so
# that tables created here are visible inside the TestClient worker.

SQLALCHEMY_TEST_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear the in-memory session store before every test.

    The session service (``app.services.session``) keeps sessions in a
    module-level dict that persists across test functions.  Without this
    fixture, a login performed in one test would leak into the next.
    """
    from app.services.session import _sessions

    _sessions.clear()
    yield
    _sessions.clear()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database schema and yield a session for one test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI ``TestClient`` with an overridden ``get_db`` dependency.

    A *new* session is created per request inside ``override_get_db`` so
    that endpoint-level ``db.commit()`` / ``db.close()`` never interfere
    with the fixture-managed session.
    """

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client):
    """A test client that has an active session cookie."""
    client.post("/api/session/login", json={"username": "admin", "password": "admin"})
    return client
