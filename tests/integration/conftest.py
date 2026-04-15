"""Shared fixtures for integration tests.

This conftest provides database fixtures that allow integration tests to
exercise the scoring pipeline end-to-end using the same setup as the backend
unit tests.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add the backend directory to sys.path so we can import app modules
backend_dir = Path(__file__).resolve().parents[2] / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

os.environ["TESTING"] = "1"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.workspace import (  # noqa: F401
    Workspace,
    WorkspaceProfile,
    WorkspaceSettings,
)
from app.models.feed import FeedSource  # noqa: F401
from app.models.report import (  # noqa: F401
    Report,
    ReportMessage,
    FeedbackEvent,
)
from app.models.content import (  # noqa: F401
    ContentItem,
    ContentCluster,
)
from app.models.run import (  # noqa: F401
    ProcessingRun,
    ProcessingRunEvent,
)
from app.models.preferences import (  # noqa: F401
    TopicPreference,
    SourcePreference,
    EntityPreference,
)
from app.models.user import User  # noqa: F401

# SQLite in-memory database for testing
SQLALCHEMY_TEST_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    """Replace real Redis with fakeredis for all tests."""
    import fakeredis
    import app.services.redis_session as rs_mod

    rs_mod._redis_client = None

    _fake_store = fakeredis.FakeRedis(decode_responses=True)

    def _fake_from_url(url, **kwargs):
        return _fake_store

    monkeypatch.setattr("redis.from_url", _fake_from_url)
    yield _fake_store

    _fake_store.flushall()
    rs_mod._redis_client = None


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
