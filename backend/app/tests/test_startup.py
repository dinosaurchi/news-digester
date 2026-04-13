"""Tests for startup failure behavior.

When the application starts in production mode (TESTING != "1"), critical
initialization steps must cause the process to abort on failure.  These
tests verify that migration and seed/bootstrap failures both raise
``SystemExit`` with an informative message.

The actual ``startup`` function is registered as a FastAPI lifecycle event
but is still a regular callable, so we invoke it directly while temporarily
disabling the ``TESTING`` guard.
"""

import subprocess
from unittest.mock import MagicMock

import pytest


class TestStartupMigrationFailure:
    """Alembic migration failure must abort the process."""

    def test_migration_failure_raises_system_exit(self, monkeypatch):
        """subprocess.CalledProcessError from alembic raises SystemExit."""
        monkeypatch.delenv("TESTING", raising=False)

        mock_error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["alembic", "upgrade", "head"],
        )
        mock_error.stderr = b"relation does not exist\n"
        monkeypatch.setattr("subprocess.run", MagicMock(side_effect=mock_error))

        from app.main import startup

        with pytest.raises(SystemExit, match="Database migration failed"):
            startup()

    def test_migration_failure_includes_stderr_detail(self, monkeypatch):
        """SystemExit message includes alembic stderr for diagnostics."""
        monkeypatch.delenv("TESTING", raising=False)

        error_detail = "Column 'foo' not found"
        mock_error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["alembic", "upgrade", "head"],
        )
        mock_error.stderr = error_detail.encode()
        monkeypatch.setattr("subprocess.run", MagicMock(side_effect=mock_error))

        from app.main import startup

        with pytest.raises(SystemExit, match=error_detail):
            startup()


class TestStartupSeedFailure:
    """Seed / admin-bootstrap failure must abort the process."""

    def test_seed_bootstrap_failure_raises_system_exit(self, monkeypatch):
        """Exception during seed/bootstrap raises SystemExit."""
        monkeypatch.delenv("TESTING", raising=False)

        # Let migration succeed
        monkeypatch.setattr(
            "subprocess.run",
            MagicMock(return_value=MagicMock(returncode=0)),
        )

        # Make SessionLocal raise to simulate a DB connection failure
        def _boom():
            raise RuntimeError("connection refused")

        monkeypatch.setattr("app.db.session.SessionLocal", _boom)

        from app.main import startup

        with pytest.raises(SystemExit, match="Seed/bootstrap failed") as exc_info:
            startup()

        assert "connection refused" in str(exc_info.value)
