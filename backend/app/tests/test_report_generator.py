"""Tests for the report generation module (report_generator.py)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.models.content import ContentItem
from app.models.report import Report, ReportMessage
from app.models.run import ProcessingRun
from app.models.workspace import Workspace, WorkspaceProfile, WorkspaceSettings
from app.services.opencode_client import (
    OpenCodeClient,
    OpenCodeResponseError,
    OpenCodeTimeoutError,
    OpenCodeUnavailableError,
    ReportResult,
)
from app.services.report_generator import generate_report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workspace(db) -> Workspace:
    """Create a workspace with profile and settings."""
    ws = Workspace(name="Test", customer="TestCo")
    db.add(ws)
    db.flush()

    profile = WorkspaceProfile(
        workspace_id=ws.id,
        priority_themes=["ai", "finance"],
    )
    db.add(profile)

    settings = WorkspaceSettings(
        workspace_id=ws.id,
    )
    db.add(settings)
    db.flush()
    return ws


def _make_run(db, workspace_id: str) -> ProcessingRun:
    """Create a processing run."""
    run = ProcessingRun(
        workspace_id=workspace_id,
        run_type="manual",
        status="running",
    )
    db.add(run)
    db.flush()
    return run


def _make_item(
    db,
    workspace_id: str,
    *,
    title: str = "Article",
    published_at: datetime | None = None,
    final_score: float = 0.8,
    summary_snippet: str = "A summary",
) -> ContentItem:
    """Create a ContentItem with sensible defaults."""
    if published_at is None:
        published_at = datetime.now(timezone.utc)
    item = ContentItem(
        workspace_id=workspace_id,
        title=title,
        url=f"https://example.com/{title}",
        source_name="Example Source",
        content_type="news",
        summary_snippet=summary_snippet,
        published_at=published_at,
        status="included",
        final_score=final_score,
    )
    db.add(item)
    db.flush()
    return item


def _make_enabled_client() -> OpenCodeClient:
    """Create an OpenCodeClient (mocked at call site)."""
    return OpenCodeClient(
        base_url="http://localhost:9001",
        timeout=30,
        default_model="test-model",
    )


def _make_mock_client(
    markdown: str = "# TestCo — Daily News Digest\n\nLLM report body.",
) -> OpenCodeClient:
    """Create an OpenCodeClient with generate_report_markdown mocked to return *markdown*."""
    client = _make_enabled_client()
    client.generate_report_markdown = MagicMock(  # type: ignore[assignment]
        return_value=ReportResult(markdown=markdown, model="test-model"),
    )
    return client


# ---------------------------------------------------------------------------
# 1. LLM report generation path (mocked)
# ---------------------------------------------------------------------------


class TestLLMReportGeneration:
    """LLM-based report generation returns markdown from the model."""

    def test_llm_generation_returns_markdown(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        item = _make_item(db_session, ws.id, title="LLM Article")

        client = _make_enabled_client()
        client.generate_report_markdown = MagicMock(  # type: ignore[assignment]
            return_value=ReportResult(
                markdown="# LLM Generated Report\n\nAI-powered content.",
                model="test-model",
            )
        )

        report = generate_report(db_session, ws, [item], run, opencode_client=client)

        assert report.markdown_body == "# LLM Generated Report\n\nAI-powered content."

    def test_llm_called_with_correct_args(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        pub_date = datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        item = _make_item(
            db_session,
            ws.id,
            title="Test Item",
            published_at=pub_date,
            final_score=0.92,
            summary_snippet="Test summary",
        )

        client = _make_enabled_client()
        client.generate_report_markdown = MagicMock(  # type: ignore[assignment]
            return_value=ReportResult(markdown="# Report")
        )

        generate_report(db_session, ws, [item], run, opencode_client=client)

        client.generate_report_markdown.assert_called_once()
        call_args = client.generate_report_markdown.call_args
        sent_items = call_args[0][0]
        sent_context = call_args[0][1]
        sent_period = call_args[0][2]

        assert len(sent_items) == 1
        assert sent_items[0]["id"] == item.id
        assert sent_items[0]["title"] == "Test Item"
        assert sent_items[0]["summary"] == "Test summary"
        assert sent_items[0]["score"] == 0.92
        assert sent_context["workspace_id"] == ws.id
        assert sent_context["customer"] == "TestCo"
        assert sent_context["priority_themes"] == ["ai", "finance"]
        assert "2025-06-15" in sent_period["start"]


# ---------------------------------------------------------------------------
# 3. Empty shortlist: produces minimal report
# ---------------------------------------------------------------------------


class TestEmptyShortlist:
    """Empty shortlist produces a report via the LLM path."""

    def test_empty_shortlist_produces_report(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        client = _make_mock_client(
            markdown="# TestCo — Daily News Digest\n\nNo items found."
        )

        report = generate_report(db_session, ws, [], run, opencode_client=client)

        assert report.markdown_body is not None
        assert "No items found" in report.markdown_body

    def test_empty_shortlist_sources_is_empty_list(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        client = _make_mock_client()

        report = generate_report(db_session, ws, [], run, opencode_client=client)

        assert report.metadata_json["sources"] == []


# ---------------------------------------------------------------------------
# 4. Source references included in metadata
# ---------------------------------------------------------------------------


class TestSourceMetadata:
    """Report and message metadata include source content item IDs."""

    def test_report_metadata_has_sources(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        item_a = _make_item(db_session, ws.id, title="A")
        item_b = _make_item(db_session, ws.id, title="B")
        client = _make_mock_client()

        report = generate_report(
            db_session, ws, [item_a, item_b], run, opencode_client=client
        )

        assert report.metadata_json is not None
        sources = report.metadata_json["sources"]
        assert len(sources) == 2
        assert item_a.id in sources
        assert item_b.id in sources

    def test_message_metadata_has_sources(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        item = _make_item(db_session, ws.id, title="A")
        client = _make_mock_client()

        report = generate_report(db_session, ws, [item], run, opencode_client=client)

        messages = (
            db_session.query(ReportMessage)
            .filter(ReportMessage.thread_id == report.id)
            .all()
        )
        assert len(messages) == 1
        msg = messages[0]
        assert msg.metadata_json is not None
        assert item.id in msg.metadata_json["sources"]
        assert msg.metadata_json["reportId"] == report.id

    def test_message_thread_id_matches_report_id(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        item = _make_item(db_session, ws.id, title="A")
        client = _make_mock_client()

        report = generate_report(db_session, ws, [item], run, opencode_client=client)

        messages = (
            db_session.query(ReportMessage)
            .filter(ReportMessage.thread_id == report.id)
            .all()
        )
        assert len(messages) == 1
        assert messages[0].thread_id == report.id

    def test_empty_shortlist_sources_is_empty_list(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        client = _make_mock_client()

        report = generate_report(db_session, ws, [], run, opencode_client=client)

        assert report.metadata_json["sources"] == []


# ---------------------------------------------------------------------------
# 5. Report period matches input period
# ---------------------------------------------------------------------------


class TestReportPeriod:
    """Report period_start and period_end match the shortlist item dates."""

    def test_period_from_single_item(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        pub_date = datetime(2025, 3, 20, 10, 0, 0, tzinfo=timezone.utc)
        item = _make_item(db_session, ws.id, title="A", published_at=pub_date)
        client = _make_mock_client()

        report = generate_report(
            db_session,
            ws,
            [item],
            run,
            opencode_client=client,
        )

        # Get fresh instance to verify flushed values
        report = db_session.get(Report, report.id)
        assert report.period_start == pub_date
        assert report.period_end == pub_date

    def test_period_spans_earliest_to_latest(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)

        early = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        late = datetime(2025, 3, 31, 23, 59, 59, tzinfo=timezone.utc)
        item_early = _make_item(db_session, ws.id, title="Early", published_at=early)
        item_late = _make_item(db_session, ws.id, title="Late", published_at=late)
        client = _make_mock_client()

        report = generate_report(
            db_session, ws, [item_early, item_late], run, opencode_client=client
        )

        report = db_session.get(Report, report.id)
        assert report.period_start == early
        assert report.period_end == late

    def test_period_uses_now_when_no_dates(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        item = _make_item(
            db_session,
            ws.id,
            title="No Date",
            published_at=None,
        )
        client = _make_mock_client()

        report = generate_report(db_session, ws, [item], run, opencode_client=client)

        report = db_session.get(Report, report.id)
        assert report.period_start is not None
        assert report.period_end is not None

    def test_period_in_markdown_matches_report_period(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)

        early = datetime(2025, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
        late = datetime(2025, 2, 14, 0, 0, 0, tzinfo=timezone.utc)
        item_early = _make_item(db_session, ws.id, title="Early", published_at=early)
        item_late = _make_item(db_session, ws.id, title="Late", published_at=late)
        client = _make_mock_client(
            markdown="# TestCo — Daily News Digest\n\n**Period**: 2025-02-01 to 2025-02-14\n\nContent."
        )

        report = generate_report(
            db_session, ws, [item_early, item_late], run, opencode_client=client
        )

        assert "2025-02-01" in report.markdown_body
        assert "2025-02-14" in report.markdown_body


# ---------------------------------------------------------------------------
# 6. LLM failure: raises exception (does NOT fall back)
# ---------------------------------------------------------------------------


class TestLLMFailure:
    """LLM failures propagate as exceptions — no silent fallback."""

    def test_unavailable_error_propagates(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        item = _make_item(db_session, ws.id, title="A")

        client = _make_enabled_client()
        client.generate_report_markdown = MagicMock(  # type: ignore[assignment]
            side_effect=OpenCodeUnavailableError("adapter unreachable"),
        )

        with pytest.raises(OpenCodeUnavailableError, match="unreachable"):
            generate_report(db_session, ws, [item], run, opencode_client=client)

    def test_timeout_error_propagates(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        item = _make_item(db_session, ws.id, title="A")

        client = _make_enabled_client()
        client.generate_report_markdown = MagicMock(  # type: ignore[assignment]
            side_effect=OpenCodeTimeoutError("timed out"),
        )

        with pytest.raises(OpenCodeTimeoutError, match="timed out"):
            generate_report(db_session, ws, [item], run, opencode_client=client)

    def test_response_error_propagates(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        item = _make_item(db_session, ws.id, title="A")

        client = _make_enabled_client()
        client.generate_report_markdown = MagicMock(  # type: ignore[assignment]
            side_effect=OpenCodeResponseError("bad response"),
        )

        with pytest.raises(OpenCodeResponseError, match="bad response"):
            generate_report(db_session, ws, [item], run, opencode_client=client)

    def test_llm_failure_does_not_create_report(self, db_session):
        """When LLM fails, no Report or ReportMessage should be persisted."""
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        item = _make_item(db_session, ws.id, title="A")

        client = _make_enabled_client()
        client.generate_report_markdown = MagicMock(  # type: ignore[assignment]
            side_effect=OpenCodeUnavailableError("down"),
        )

        with pytest.raises(OpenCodeUnavailableError):
            generate_report(db_session, ws, [item], run, opencode_client=client)

        # No report should exist
        reports = db_session.query(Report).all()
        assert len(reports) == 0

        # No messages should exist
        messages = db_session.query(ReportMessage).all()
        assert len(messages) == 0


# ---------------------------------------------------------------------------
# 7. Report structure and field correctness
# ---------------------------------------------------------------------------


class TestReportStructure:
    """Report record has correct field values."""

    def test_report_links_to_workspace_and_run(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        item = _make_item(db_session, ws.id, title="A")
        client = _make_mock_client()

        report = generate_report(db_session, ws, [item], run, opencode_client=client)

        assert report.workspace_id == ws.id
        assert report.run_id == run.id

    def test_report_status_is_published(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        item = _make_item(db_session, ws.id, title="A")
        client = _make_mock_client()

        report = generate_report(db_session, ws, [item], run, opencode_client=client)

        assert report.status == "published"

    def test_report_has_id_assigned(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        item = _make_item(db_session, ws.id, title="A")
        client = _make_mock_client()

        report = generate_report(db_session, ws, [item], run, opencode_client=client)

        assert report.id is not None
        assert len(report.id) > 0

    def test_report_title_uses_customer_name(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        item = _make_item(db_session, ws.id, title="A")
        client = _make_mock_client()

        report = generate_report(db_session, ws, [item], run, opencode_client=client)

        assert "TestCo" in report.title
        assert "Daily News Digest" in report.title

    def test_message_content_matches_report_body(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        item = _make_item(db_session, ws.id, title="A")
        client = _make_mock_client()

        report = generate_report(db_session, ws, [item], run, opencode_client=client)

        messages = (
            db_session.query(ReportMessage)
            .filter(ReportMessage.thread_id == report.id)
            .all()
        )
        assert len(messages) == 1
        assert messages[0].content == report.markdown_body

    def test_message_role_is_system(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        item = _make_item(db_session, ws.id, title="A")
        client = _make_mock_client()

        report = generate_report(db_session, ws, [item], run, opencode_client=client)

        messages = (
            db_session.query(ReportMessage)
            .filter(ReportMessage.thread_id == report.id)
            .all()
        )
        assert messages[0].role == "system"


# ---------------------------------------------------------------------------
# 8. Mandatory OpenCode client requirement
# ---------------------------------------------------------------------------


class TestMandatoryOpenCodeClient:
    """OpenCode client is a required parameter — no disabled-mode fallback."""

    def test_missing_opencode_client_raises_type_error(self, db_session):
        """Calling generate_report without opencode_client is a TypeError."""
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        item = _make_item(db_session, ws.id, title="A")

        with pytest.raises(TypeError):
            generate_report(db_session, ws, [item], run)

    def test_none_opencode_client_raises_error(self, db_session):
        """Passing opencode_client=None fails — not a valid client.

        The function does not have runtime type-checking for None, so it
        raises AttributeError when trying to call methods on None.  Either
        TypeError (from missing keyword) or AttributeError (from None) is
        acceptable — the point is it fails explicitly.
        """
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        item = _make_item(db_session, ws.id, title="A")

        with pytest.raises((TypeError, AttributeError)):
            generate_report(db_session, ws, [item], run, opencode_client=None)
