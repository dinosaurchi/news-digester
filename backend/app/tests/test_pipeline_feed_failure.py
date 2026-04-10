"""Tests for feed failure and recovery in the ingestion pipeline.

Verifies that:
- The pipeline continues processing when some feeds fail
- Previously-failing feeds recover when they succeed
- The pipeline completes gracefully when all feeds fail
- FeedFetchResult correctly represents error/success states
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.feed import FeedSource
from app.models.report import Report
from app.models.workspace import Workspace
from app.services.pipeline import execute_workspace_run
from app.services.pipeline_steps import FeedFetchResult, fetch_feed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workspace(db, name="Test WS", customer="Co") -> Workspace:
    """Create and persist a Workspace in the DB."""
    ws = Workspace(name=name, customer=customer)
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


def _make_feed(
    db,
    workspace_id: str,
    name: str = "Test Feed",
    url: str = "https://example.com/feed",
    feed_type: str = "rss",
    status: str = "healthy",
    **kwargs,
) -> FeedSource:
    """Create and persist a FeedSource in the DB."""
    feed = FeedSource(
        workspace_id=workspace_id,
        name=name,
        url=url,
        type=feed_type,
        status=status,
        **kwargs,
    )
    db.add(feed)
    db.commit()
    db.refresh(feed)
    return feed


def _make_entry(title: str = "Article", url: str = "https://example.com/1") -> dict:
    """Create a minimal raw feed-entry dict."""
    return {
        "title": title,
        "url": url,
        "source_name": "Example",
        "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
        "author": "Alice",
        "summary": "Summary",
        "raw_text": "Content",
    }


def _fake_generate_report(db, workspace, items, run, **kwargs):
    """Create a real Report row so that db.refresh() works."""
    report = Report(
        workspace_id=workspace.id,
        title="Test Report",
        status="draft",
        run_id=run.id,
    )
    db.add(report)
    db.flush()
    return report


def _setup_downstream_mocks(mock_cluster, mock_score, mock_report, mock_shortlist):
    """Configure common return values for downstream pipeline mocks.

    NOTE: The @patch decorators are applied bottom-to-top, so parameter
    order is: mock_fetch, mock_cluster, mock_score, mock_report,
    mock_shortlist.  We only need to set up the four downstream ones here.
    """
    mock_cluster.return_value = {
        "items_clustered": 0,
        "clusters_created": 0,
        "singleton_clusters": 0,
    }
    mock_score.return_value = {
        "included_count": 0,
        "excluded_count": 0,
        "avg_score": 0.0,
    }
    mock_report.side_effect = _fake_generate_report
    mock_shortlist.return_value = []


# ===========================================================================
# 1. Partial failure — one feed fails, the other succeeds
# ===========================================================================


class TestPartialFailure:
    """Pipeline continues and processes the successful feed when one fails."""

    @patch("app.services.pipeline.select_shortlist")
    @patch("app.services.pipeline.generate_report")
    @patch("app.services.pipeline.score_content_items")
    @patch("app.services.pipeline.cluster_content_items")
    @patch("app.services.pipeline.fetch_feed")
    def test_pipeline_continues_on_partial_failure(
        self,
        mock_fetch,
        mock_cluster,
        mock_score,
        mock_report,
        mock_shortlist,
        db_session,
    ):
        ws = _make_workspace(db_session)
        feed_ok = _make_feed(
            db_session, ws.id, name="OK Feed", url="https://ok.com/feed"
        )
        feed_fail = _make_feed(
            db_session, ws.id, name="Fail Feed", url="https://fail.com/feed"
        )

        def side_effect(feed):
            if feed.id == feed_ok.id:
                return FeedFetchResult(
                    success=True,
                    entries=[_make_entry()],
                    error=None,
                    source_title=feed.name,
                )
            return FeedFetchResult(
                success=False,
                entries=[],
                error="Connection refused",
                source_title=feed.name,
            )

        mock_fetch.side_effect = side_effect
        _setup_downstream_mocks(mock_cluster, mock_score, mock_report, mock_shortlist)

        run, items, report = execute_workspace_run(db_session, ws)

        # --- Failed feed: error state recorded ---
        db_session.refresh(feed_fail)
        assert feed_fail.status == "error"
        assert feed_fail.last_error == "Connection refused"
        assert feed_fail.last_error_at is not None

        # --- Successful feed: healthy state, entries imported ---
        db_session.refresh(feed_ok)
        assert feed_ok.status == "healthy"
        assert feed_ok.last_error is None
        assert feed_ok.last_error_at is None
        assert feed_ok.last_fetched_at is not None

        # --- Run completed successfully with 1 article ---
        assert run.status == "success"
        assert len(items) == 1

    @patch("app.services.pipeline.select_shortlist")
    @patch("app.services.pipeline.generate_report")
    @patch("app.services.pipeline.score_content_items")
    @patch("app.services.pipeline.cluster_content_items")
    @patch("app.services.pipeline.fetch_feed")
    def test_failed_feed_does_not_update_last_fetched_at(
        self,
        mock_fetch,
        mock_cluster,
        mock_score,
        mock_report,
        mock_shortlist,
        db_session,
    ):
        """A failing feed must NOT have its last_fetched_at timestamp updated."""
        ws = _make_workspace(db_session)
        # Use naive datetime since SQLite strips timezone info on round-trip
        earlier = datetime(2024, 1, 1)
        feed_fail = _make_feed(
            db_session,
            ws.id,
            name="Fail Feed",
            url="https://fail.com/feed",
            last_fetched_at=earlier,
        )
        feed_ok = _make_feed(
            db_session, ws.id, name="OK Feed", url="https://ok.com/feed"
        )

        def side_effect(feed):
            if feed.id == feed_ok.id:
                return FeedFetchResult(
                    success=True, entries=[], error=None, source_title=feed.name
                )
            return FeedFetchResult(
                success=False, entries=[], error="Timeout", source_title=feed.name
            )

        mock_fetch.side_effect = side_effect
        _setup_downstream_mocks(mock_cluster, mock_score, mock_report, mock_shortlist)

        execute_workspace_run(db_session, ws)

        db_session.refresh(feed_fail)
        # last_fetched_at should remain at the earlier value (unchanged)
        assert feed_fail.last_fetched_at is not None
        assert feed_fail.last_fetched_at == earlier


# ===========================================================================
# 2. Recovery — previously-failing feed succeeds
# ===========================================================================


class TestRecovery:
    """A feed that was in error state recovers when fetch succeeds."""

    @patch("app.services.pipeline.select_shortlist")
    @patch("app.services.pipeline.generate_report")
    @patch("app.services.pipeline.score_content_items")
    @patch("app.services.pipeline.cluster_content_items")
    @patch("app.services.pipeline.fetch_feed")
    def test_failed_feed_recovers_on_success(
        self,
        mock_fetch,
        mock_cluster,
        mock_score,
        mock_report,
        mock_shortlist,
        db_session,
    ):
        ws = _make_workspace(db_session)
        # Use naive datetime since SQLite strips timezone info on round-trip
        error_time = datetime(2024, 1, 15, 12, 0, 0)
        feed = _make_feed(
            db_session,
            ws.id,
            name="Recovery Feed",
            status="error",
            last_error="Previous: Connection refused",
            last_error_at=error_time,
        )

        mock_fetch.return_value = FeedFetchResult(
            success=True,
            entries=[_make_entry()],
            error=None,
            source_title=feed.name,
        )
        _setup_downstream_mocks(mock_cluster, mock_score, mock_report, mock_shortlist)

        run, items, report = execute_workspace_run(db_session, ws)

        db_session.refresh(feed)
        assert feed.status == "healthy"
        assert feed.last_error is None
        assert feed.last_error_at is None
        assert feed.last_fetched_at is not None
        assert feed.last_fetched_at > error_time

    @patch("app.services.pipeline.select_shortlist")
    @patch("app.services.pipeline.generate_report")
    @patch("app.services.pipeline.score_content_items")
    @patch("app.services.pipeline.cluster_content_items")
    @patch("app.services.pipeline.fetch_feed")
    def test_recovery_then_failure_transitions_back_to_error(
        self,
        mock_fetch,
        mock_cluster,
        mock_score,
        mock_report,
        mock_shortlist,
        db_session,
    ):
        """Feed recovers on first run, then fails on second run."""
        ws = _make_workspace(db_session)
        feed = _make_feed(
            db_session,
            ws.id,
            name="Flaky Feed",
            status="error",
            last_error="Initial error",
            last_error_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        # --- Run 1: success (recovery) ---
        mock_fetch.return_value = FeedFetchResult(
            success=True, entries=[], error=None, source_title=feed.name
        )
        _setup_downstream_mocks(mock_cluster, mock_score, mock_report, mock_shortlist)

        execute_workspace_run(db_session, ws)
        db_session.refresh(feed)
        assert feed.status == "healthy"
        assert feed.last_error is None

        # --- Run 2: failure ---
        mock_fetch.return_value = FeedFetchResult(
            success=False,
            entries=[],
            error="503 Service Unavailable",
            source_title=feed.name,
        )
        _setup_downstream_mocks(mock_cluster, mock_score, mock_report, mock_shortlist)

        execute_workspace_run(db_session, ws)
        db_session.refresh(feed)
        assert feed.status == "error"
        assert "503" in feed.last_error
        assert feed.last_error_at is not None


# ===========================================================================
# 3. All feeds fail
# ===========================================================================


class TestAllFeedsFail:
    """Pipeline completes gracefully when every feed fails."""

    @patch("app.services.pipeline.select_shortlist")
    @patch("app.services.pipeline.generate_report")
    @patch("app.services.pipeline.score_content_items")
    @patch("app.services.pipeline.cluster_content_items")
    @patch("app.services.pipeline.fetch_feed")
    def test_all_feeds_fail_pipeline_completes(
        self,
        mock_fetch,
        mock_cluster,
        mock_score,
        mock_report,
        mock_shortlist,
        db_session,
    ):
        ws = _make_workspace(db_session)
        feed1 = _make_feed(db_session, ws.id, name="Feed 1", url="https://f1.com/feed")
        feed2 = _make_feed(db_session, ws.id, name="Feed 2", url="https://f2.com/feed")

        mock_fetch.return_value = FeedFetchResult(
            success=False, entries=[], error="Network error", source_title="Feed"
        )
        _setup_downstream_mocks(mock_cluster, mock_score, mock_report, mock_shortlist)

        run, items, report = execute_workspace_run(db_session, ws)

        # All feeds in error state
        db_session.refresh(feed1)
        db_session.refresh(feed2)
        assert feed1.status == "error"
        assert feed1.last_error == "Network error"
        assert feed1.last_error_at is not None
        assert feed2.status == "error"
        assert feed2.last_error == "Network error"
        assert feed2.last_error_at is not None

        # Run completed with 0 articles
        assert run.status == "success"
        assert len(items) == 0

    @patch("app.services.pipeline.select_shortlist")
    @patch("app.services.pipeline.generate_report")
    @patch("app.services.pipeline.score_content_items")
    @patch("app.services.pipeline.cluster_content_items")
    @patch("app.services.pipeline.fetch_feed")
    def test_single_feed_fail_pipeline_completes(
        self,
        mock_fetch,
        mock_cluster,
        mock_score,
        mock_report,
        mock_shortlist,
        db_session,
    ):
        """Even a single failing feed (and no others) completes the run."""
        ws = _make_workspace(db_session)
        feed = _make_feed(
            db_session, ws.id, name="Only Feed", url="https://only.com/feed"
        )

        mock_fetch.return_value = FeedFetchResult(
            success=False,
            entries=[],
            error="DNS resolution failed",
            source_title=feed.name,
        )
        _setup_downstream_mocks(mock_cluster, mock_score, mock_report, mock_shortlist)

        run, items, report = execute_workspace_run(db_session, ws)

        db_session.refresh(feed)
        assert feed.status == "error"
        assert "DNS" in feed.last_error
        assert run.status == "success"
        assert len(items) == 0


# ===========================================================================
# 4. FeedFetchResult error states (fetch_feed unit tests)
# ===========================================================================


class TestFeedFetchResultErrorStates:
    """Verify fetch_feed returns correct FeedFetchResult for various inputs."""

    @patch("app.services.pipeline_steps.httpx.get")
    def test_http_error_returns_failure(self, mock_get):
        """Network-level HTTP error → success=False with error message."""
        import httpx

        mock_get.side_effect = httpx.ConnectError("Connection refused")

        feed = MagicMock(spec=FeedSource)
        feed.name = "Test Feed"
        feed.url = "https://example.com/feed"

        result = fetch_feed(feed)
        assert result.success is False
        assert "Fetch failed" in result.error
        assert result.entries == []
        assert result.source_title == "Test Feed"

    @patch("app.services.pipeline_steps.feedparser.parse")
    @patch("app.services.pipeline_steps.httpx.get")
    def test_parse_failure_returns_failure(self, mock_get, mock_parse):
        """feedparser bozo (parse error) → success=False with error message."""
        mock_resp = MagicMock()
        mock_resp.text = "<xml>data</xml>"
        mock_get.return_value = mock_resp

        # Force feedparser to report a parse error
        mock_parsed = MagicMock()
        mock_parsed.bozo = True
        mock_parsed.bozo_exception = ValueError("Malformed feed document")
        mock_parsed.entries = []
        mock_parsed.feed = {"title": "Bad Feed"}
        mock_parse.return_value = mock_parsed

        feed = MagicMock(spec=FeedSource)
        feed.name = "Bad Feed"
        feed.url = "https://example.com/bad"

        result = fetch_feed(feed)
        assert result.success is False
        assert result.error is not None
        assert "parse" in result.error.lower()
        assert result.entries == []
        assert result.source_title == "Bad Feed"

    @patch("app.services.pipeline_steps.feedparser.parse")
    @patch("app.services.pipeline_steps.httpx.get")
    def test_empty_valid_feed_returns_success_with_no_entries(
        self, mock_get, mock_parse
    ):
        """Well-formed feed with zero entries → success=True, entries=[]."""
        mock_resp = MagicMock()
        mock_resp.text = "<rss></rss>"
        mock_get.return_value = mock_resp

        mock_parsed = MagicMock()
        mock_parsed.bozo = False
        mock_parsed.entries = []
        mock_parsed.feed = {"title": "Empty Feed"}
        mock_parse.return_value = mock_parsed

        feed = MagicMock(spec=FeedSource)
        feed.name = "Empty Feed"
        feed.url = "https://example.com/empty"

        result = fetch_feed(feed)
        assert result.success is True
        assert result.entries == []
        assert result.error is None
        assert result.source_title == "Empty Feed"

    @patch("app.services.pipeline_steps.feedparser.parse")
    @patch("app.services.pipeline_steps.httpx.get")
    def test_valid_feed_with_entries_returns_success(self, mock_get, mock_parse):
        """Valid feed with articles → success=True, entries populated."""
        mock_resp = MagicMock()
        mock_resp.text = "<rss></rss>"
        mock_get.return_value = mock_resp

        entry = MagicMock()
        entry.get.side_effect = lambda key, default=None: {
            "title": "Article One",
            "link": "https://example.com/one",
            "published": "Wed, 20 Mar 2024 08:00:00 +0000",
            "author": "Alice",
            "summary": "A summary",
            "content": [{"value": "Full body"}],
        }.get(key, default)
        entry.published_parsed = None
        entry.updated_parsed = None

        mock_parsed = MagicMock()
        mock_parsed.bozo = False
        mock_parsed.entries = [entry]
        mock_parsed.feed = {"title": "News Feed"}
        mock_parse.return_value = mock_parsed

        feed = MagicMock(spec=FeedSource)
        feed.name = "News Feed"
        feed.url = "https://example.com/feed"

        result = fetch_feed(feed)
        assert result.success is True
        assert len(result.entries) == 1
        assert result.entries[0]["title"] == "Article One"
        assert result.error is None
        assert result.source_title == "News Feed"

    @patch("app.services.pipeline_steps.httpx.get")
    def test_http_timeout_returns_failure(self, mock_get):
        """HTTP timeout → success=False with error message."""
        import httpx

        mock_get.side_effect = httpx.TimeoutException("Read timed out")

        feed = MagicMock(spec=FeedSource)
        feed.name = "Slow Feed"
        feed.url = "https://slow.example.com/feed"

        result = fetch_feed(feed)
        assert result.success is False
        assert "Fetch failed" in result.error
        assert "timed out" in result.error.lower() or "timeout" in result.error.lower()
        assert result.entries == []

    @patch("app.services.pipeline_steps.httpx.get")
    def test_http_status_error_returns_failure(self, mock_get):
        """HTTP 404/500 via explicit exception → success=False."""
        import httpx

        mock_get.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

        feed = MagicMock(spec=FeedSource)
        feed.name = "Error Feed"
        feed.url = "https://error.example.com/feed"

        result = fetch_feed(feed)
        assert result.success is False
        assert "Fetch failed" in result.error
        assert result.entries == []
