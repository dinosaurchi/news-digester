import os

os.environ["TESTING"] = "1"

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
from app.models.content import (  # noqa: F401 — ensure models are registered with Base
    ContentItem,
    ContentCluster,
)
from app.models.run import (  # noqa: F401 — ensure models are registered with Base
    ProcessingRun,
    ProcessingRunEvent,
)
from app.models.preferences import (  # noqa: F401 — ensure models are registered with Base
    TopicPreference,
    SourcePreference,
    EntityPreference,
)
from app.models.user import User  # noqa: F401 — ensure model is registered with Base
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


@pytest.fixture(autouse=True)
def seed_test_admin(db_session):
    """Seed the real login user used by backend session tests."""
    from app.services.session import bootstrap_admin_user

    bootstrap_admin_user(db_session)
    db_session.commit()


@pytest.fixture(autouse=True)
def mock_opencode_client(monkeypatch):
    """Provide a default mock OpenCodeClient for the pipeline so tests don't
    make real HTTP calls.

    Only the pipeline import site is patched.  Tests that exercise the
    reports API (which creates its own OpenCodeClient) should provide their
    own mocks.
    """
    from unittest.mock import MagicMock
    from app.services.opencode_client import ShortlistResult, ReportResult

    def _passthrough_shortlist(items, workspace_context):
        return ShortlistResult(
            selected_items=items,
            rationale="Test mock",
        )

    def _passthrough_report(items, workspace_context, period):
        customer = workspace_context.get("customer", "Test")
        title = f"{customer} — Daily News Digest"
        period_str = f"{period.get('start', '')} to {period.get('end', '')}"

        if not items:
            return ReportResult(
                markdown=f"# {title}\n\n**Period**: {period_str}\n\n## Summary\n\nNo items found for this reporting period.",
            )

        highlights = []
        for i, item in enumerate(items, 1):
            summary = item.get("summary", "")
            url = item.get("url", "")
            link = f" [Read more]({url})" if url else ""
            highlights.append(f"{i}. {item.get('title', 'Untitled')} — {summary}{link}")

        sources = []
        for item in items:
            published = item.get("published_at", "")
            score = item.get("score", 0)
            sources.append(
                f"### {item.get('title', 'Untitled')}\n\n"
                f"Published: {published}\n\n"
                f"Score: {score}\n\n"
                f"{item.get('summary', '')}\n\n"
                f"[Read more]({item.get('url', '')})"
            )

        return ReportResult(
            markdown=(
                f"# {title}\n\n"
                f"**Period**: {period_str}\n\n"
                f"## Top Highlights\n\n"
                + "\n\n".join(highlights)
                + "\n\n## Source Details\n\n"
                + "\n\n".join(sources)
            ),
        )

    mock_client = MagicMock()
    mock_client.refine_shortlist.side_effect = _passthrough_shortlist
    mock_client.generate_report_markdown.side_effect = _passthrough_report

    monkeypatch.setattr(
        "app.services.pipeline.OpenCodeClient",
        lambda **kwargs: mock_client,
    )


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
