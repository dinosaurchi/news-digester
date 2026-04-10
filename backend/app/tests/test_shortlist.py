"""Tests for the shortlist selection module (shortlist.py)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.models.content import ContentItem
from app.models.run import ProcessingRun
from app.models.workspace import Workspace, WorkspaceProfile, WorkspaceSettings
from app.services.opencode_client import (
    OpenCodeClient,
    OpenCodeResponseError,
    OpenCodeTimeoutError,
    OpenCodeUnavailableError,
    ShortlistResult,
)
from app.services.shortlist import select_shortlist


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workspace(
    db,
    *,
    max_articles: int | None = None,
) -> Workspace:
    """Create a workspace with optional settings."""
    ws = Workspace(name="Test", customer="TestCo")
    db.add(ws)
    db.flush()

    profile = WorkspaceProfile(
        workspace_id=ws.id,
        priority_themes=["ai"],
    )
    db.add(profile)

    thresholds: dict = {}
    if max_articles is not None:
        thresholds["maxArticlesPerReport"] = max_articles

    settings = WorkspaceSettings(
        workspace_id=ws.id,
        thresholds=thresholds or None,
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
    status: str = "included",
    final_score: float = 0.5,
    cluster_id: str | None = None,
    is_lead: bool = False,
) -> ContentItem:
    """Create a ContentItem with sensible defaults."""
    item = ContentItem(
        workspace_id=workspace_id,
        title=title,
        url=f"https://example.com/{title}",
        source_name="Example",
        content_type="news",
        summary_snippet=f"Summary for {title}",
        published_at=datetime.now(timezone.utc),
        status=status,
        final_score=final_score,
        cluster_id=cluster_id,
        is_lead=is_lead,
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


def _make_passthrough_client() -> OpenCodeClient:
    """Create a mock OpenCode client that returns items unchanged.

    Used by tests that exercise pre-processing logic (filtering, dedup,
    capping) without needing to verify LLM reordering behaviour.
    """
    client = _make_enabled_client()

    def _passthrough(item_dicts, workspace_context):
        return ShortlistResult(
            selected_items=list(item_dicts),
            rationale="passthrough",
        )

    client.refine_shortlist = MagicMock(side_effect=_passthrough)  # type: ignore[assignment]
    return client


# ---------------------------------------------------------------------------
# 1. Basic shortlist selection: top N items by score
# ---------------------------------------------------------------------------


class TestBasicShortlistSelection:
    """Shortlist selects top-scoring included items."""

    def test_selects_included_items_sorted_by_score(self, db_session):
        ws = _make_workspace(db_session, max_articles=5)
        run = _make_run(db_session, ws.id)
        client = _make_passthrough_client()

        items = [
            _make_item(db_session, ws.id, title="Low", final_score=0.1),
            _make_item(db_session, ws.id, title="High", final_score=0.9),
            _make_item(db_session, ws.id, title="Mid", final_score=0.5),
        ]

        result = select_shortlist(db_session, items, ws, run, opencode_client=client)

        assert len(result) == 3
        assert [i.title for i in result] == ["High", "Mid", "Low"]

    def test_excludes_non_included_items(self, db_session):
        ws = _make_workspace(db_session, max_articles=10)
        run = _make_run(db_session, ws.id)
        client = _make_passthrough_client()

        items = [
            _make_item(
                db_session, ws.id, title="Included", status="included", final_score=0.8
            ),
            _make_item(
                db_session, ws.id, title="Excluded", status="excluded", final_score=0.9
            ),
            _make_item(
                db_session, ws.id, title="Pending", status="pending", final_score=0.7
            ),
        ]

        result = select_shortlist(db_session, items, ws, run, opencode_client=client)

        assert len(result) == 1
        assert result[0].title == "Included"


# ---------------------------------------------------------------------------
# 2. Cluster dedup: only one item per cluster
# ---------------------------------------------------------------------------


class TestClusterDedup:
    """Only one item per cluster is selected."""

    def test_keeps_lead_item_from_cluster(self, db_session):
        ws = _make_workspace(db_session, max_articles=10)
        run = _make_run(db_session, ws.id)
        client = _make_passthrough_client()

        cluster_id = "cluster-1"
        items = [
            _make_item(
                db_session,
                ws.id,
                title="Lead",
                final_score=0.3,
                cluster_id=cluster_id,
                is_lead=True,
            ),
            _make_item(
                db_session,
                ws.id,
                title="Non-lead A",
                final_score=0.8,
                cluster_id=cluster_id,
                is_lead=False,
            ),
            _make_item(
                db_session,
                ws.id,
                title="Non-lead B",
                final_score=0.7,
                cluster_id=cluster_id,
                is_lead=False,
            ),
        ]

        result = select_shortlist(db_session, items, ws, run, opencode_client=client)

        cluster_items = [i for i in result if i.cluster_id == cluster_id]
        assert len(cluster_items) == 1
        assert cluster_items[0].title == "Lead"

    def test_keeps_highest_scored_when_no_lead(self, db_session):
        ws = _make_workspace(db_session, max_articles=10)
        run = _make_run(db_session, ws.id)
        client = _make_passthrough_client()

        cluster_id = "cluster-2"
        items = [
            _make_item(
                db_session,
                ws.id,
                title="Low",
                final_score=0.2,
                cluster_id=cluster_id,
                is_lead=False,
            ),
            _make_item(
                db_session,
                ws.id,
                title="High",
                final_score=0.9,
                cluster_id=cluster_id,
                is_lead=False,
            ),
            _make_item(
                db_session,
                ws.id,
                title="Mid",
                final_score=0.5,
                cluster_id=cluster_id,
                is_lead=False,
            ),
        ]

        result = select_shortlist(db_session, items, ws, run, opencode_client=client)

        cluster_items = [i for i in result if i.cluster_id == cluster_id]
        assert len(cluster_items) == 1
        assert cluster_items[0].title == "High"

    def test_different_clusters_are_independent(self, db_session):
        ws = _make_workspace(db_session, max_articles=10)
        run = _make_run(db_session, ws.id)
        client = _make_passthrough_client()

        items = [
            _make_item(
                db_session,
                ws.id,
                title="Cluster A lead",
                final_score=0.4,
                cluster_id="cluster-a",
                is_lead=True,
            ),
            _make_item(
                db_session,
                ws.id,
                title="Cluster A other",
                final_score=0.9,
                cluster_id="cluster-a",
                is_lead=False,
            ),
            _make_item(
                db_session,
                ws.id,
                title="Cluster B lead",
                final_score=0.6,
                cluster_id="cluster-b",
                is_lead=True,
            ),
            _make_item(
                db_session,
                ws.id,
                title="Cluster B other",
                final_score=0.8,
                cluster_id="cluster-b",
                is_lead=False,
            ),
        ]

        result = select_shortlist(db_session, items, ws, run, opencode_client=client)

        assert len(result) == 2
        titles = {i.title for i in result}
        assert titles == {"Cluster A lead", "Cluster B lead"}

    def test_unclustered_items_are_all_kept(self, db_session):
        """Items with cluster_id=None are not deduplicated."""
        ws = _make_workspace(db_session, max_articles=10)
        run = _make_run(db_session, ws.id)
        client = _make_passthrough_client()

        items = [
            _make_item(
                db_session,
                ws.id,
                title="No cluster A",
                final_score=0.7,
                cluster_id=None,
            ),
            _make_item(
                db_session,
                ws.id,
                title="No cluster B",
                final_score=0.6,
                cluster_id=None,
            ),
        ]

        result = select_shortlist(db_session, items, ws, run, opencode_client=client)

        assert len(result) == 2


# ---------------------------------------------------------------------------
# 3. Shortlist cap: respects maxArticlesPerReport
# ---------------------------------------------------------------------------


class TestShortlistCap:
    """Shortlist is capped at maxArticlesPerReport."""

    def test_caps_at_setting_value(self, db_session):
        ws = _make_workspace(db_session, max_articles=3)
        run = _make_run(db_session, ws.id)
        client = _make_passthrough_client()

        items = [
            _make_item(db_session, ws.id, title=f"Article {i}", final_score=float(i))
            for i in range(10)
        ]

        result = select_shortlist(db_session, items, ws, run, opencode_client=client)

        assert len(result) == 3
        # Should be the top 3 by score
        assert result[0].final_score == 9.0
        assert result[1].final_score == 8.0
        assert result[2].final_score == 7.0

    def test_uses_default_cap_when_no_setting(self, db_session):
        """Default cap is 15 when maxArticlesPerReport is not set."""
        from app.services.shortlist import _DEFAULT_MAX_ARTICLES

        ws = _make_workspace(db_session, max_articles=None)
        run = _make_run(db_session, ws.id)
        client = _make_passthrough_client()

        items = [
            _make_item(db_session, ws.id, title=f"Article {i}", final_score=float(i))
            for i in range(20)
        ]

        result = select_shortlist(db_session, items, ws, run, opencode_client=client)

        assert len(result) == _DEFAULT_MAX_ARTICLES

    def test_uses_default_cap_when_no_settings_object(self, db_session):
        """Default cap is 15 when workspace has no settings."""
        from app.services.shortlist import _DEFAULT_MAX_ARTICLES

        from app.models.workspace import Workspace

        ws = Workspace(name="NoSettings", customer="TestCo")
        db_session.add(ws)
        db_session.flush()
        run = _make_run(db_session, ws.id)
        client = _make_passthrough_client()

        items = [
            _make_item(db_session, ws.id, title=f"Article {i}", final_score=float(i))
            for i in range(20)
        ]

        result = select_shortlist(db_session, items, ws, run, opencode_client=client)

        assert len(result) == _DEFAULT_MAX_ARTICLES


# ---------------------------------------------------------------------------
# 4. Empty input → empty shortlist
# ---------------------------------------------------------------------------


class TestEmptyInput:
    """Empty input returns empty shortlist."""

    def test_empty_items_list(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        client = _make_passthrough_client()

        result = select_shortlist(db_session, [], ws, run, opencode_client=client)

        assert result == []

    def test_no_included_items(self, db_session):
        ws = _make_workspace(db_session)
        run = _make_run(db_session, ws.id)
        client = _make_passthrough_client()

        items = [
            _make_item(db_session, ws.id, title="Excluded", status="excluded"),
            _make_item(db_session, ws.id, title="Pending", status="pending"),
        ]

        result = select_shortlist(db_session, items, ws, run, opencode_client=client)

        assert result == []


# ---------------------------------------------------------------------------
# 5. Fewer items than cap → all included
# ---------------------------------------------------------------------------


class TestFewerItemsThanCap:
    """When there are fewer items than the cap, all are included."""

    def test_all_items_included_when_below_cap(self, db_session):
        ws = _make_workspace(db_session, max_articles=15)
        run = _make_run(db_session, ws.id)
        client = _make_passthrough_client()

        items = [
            _make_item(db_session, ws.id, title=f"Article {i}", final_score=float(i))
            for i in range(5)
        ]

        result = select_shortlist(db_session, items, ws, run, opencode_client=client)

        assert len(result) == 5

    def test_single_item(self, db_session):
        ws = _make_workspace(db_session, max_articles=10)
        run = _make_run(db_session, ws.id)
        client = _make_passthrough_client()

        items = [
            _make_item(db_session, ws.id, title="Only one", final_score=0.8),
        ]

        result = select_shortlist(db_session, items, ws, run, opencode_client=client)

        assert len(result) == 1
        assert result[0].title == "Only one"


# ---------------------------------------------------------------------------
# 6. LLM refinement path (mocked): successful refinement
# ---------------------------------------------------------------------------


class TestLLMRefinement:
    """LLM refinement successfully reorders/filters the shortlist."""

    def test_llm_reorders_shortlist(self, db_session):
        ws = _make_workspace(db_session, max_articles=10)
        run = _make_run(db_session, ws.id)

        item_a = _make_item(db_session, ws.id, title="A", final_score=0.9)
        item_b = _make_item(db_session, ws.id, title="B", final_score=0.8)
        item_c = _make_item(db_session, ws.id, title="C", final_score=0.7)

        # LLM selects B first, then A (different order from score)
        client = _make_enabled_client()
        client.refine_shortlist = MagicMock(  # type: ignore[assignment]
            return_value=ShortlistResult(
                selected_items=[
                    {"id": item_b.id, "title": "B"},
                    {"id": item_a.id, "title": "A"},
                ],
                rationale="B is more timely",
            )
        )

        result = select_shortlist(
            db_session,
            [item_a, item_b, item_c],
            ws,
            run,
            opencode_client=client,
        )

        assert len(result) == 2
        assert result[0].id == item_b.id
        assert result[1].id == item_a.id

    def test_llm_filters_shortlist(self, db_session):
        ws = _make_workspace(db_session, max_articles=10)
        run = _make_run(db_session, ws.id)

        item_a = _make_item(db_session, ws.id, title="A", final_score=0.9)
        item_b = _make_item(db_session, ws.id, title="B", final_score=0.8)
        item_c = _make_item(db_session, ws.id, title="C", final_score=0.7)

        # LLM selects only one item
        client = _make_enabled_client()
        client.refine_shortlist = MagicMock(  # type: ignore[assignment]
            return_value=ShortlistResult(
                selected_items=[
                    {"id": item_b.id, "title": "B"},
                ],
                rationale="Only B is relevant this week",
            )
        )

        result = select_shortlist(
            db_session,
            [item_a, item_b, item_c],
            ws,
            run,
            opencode_client=client,
        )

        assert len(result) == 1
        assert result[0].id == item_b.id

    def test_llm_called_with_correct_args(self, db_session):
        ws = _make_workspace(db_session, max_articles=10)
        run = _make_run(db_session, ws.id)

        item_a = _make_item(db_session, ws.id, title="A", final_score=0.9)

        client = _make_enabled_client()
        client.refine_shortlist = MagicMock(  # type: ignore[assignment]
            return_value=ShortlistResult(
                selected_items=[{"id": item_a.id, "title": "A"}],
                rationale="OK",
            )
        )

        select_shortlist(
            db_session,
            [item_a],
            ws,
            run,
            opencode_client=client,
        )

        client.refine_shortlist.assert_called_once()
        call_args = client.refine_shortlist.call_args
        # Positional args: items, workspace_context
        sent_items = call_args[0][0]
        sent_context = call_args[0][1]

        assert len(sent_items) == 1
        assert sent_items[0]["id"] == item_a.id
        assert sent_items[0]["title"] == "A"
        assert sent_context["workspace_id"] == ws.id
        assert sent_context["customer"] == ws.customer


# ---------------------------------------------------------------------------
# 7. LLM failure: raises exception (does NOT fall back)
# ---------------------------------------------------------------------------


class TestLLMFailure:
    """LLM failures propagate as exceptions — no silent fallback."""

    def test_unavailable_error_propagates(self, db_session):
        ws = _make_workspace(db_session, max_articles=10)
        run = _make_run(db_session, ws.id)

        item = _make_item(db_session, ws.id, title="A", final_score=0.9)

        client = _make_enabled_client()
        client.refine_shortlist = MagicMock(  # type: ignore[assignment]
            side_effect=OpenCodeUnavailableError("adapter unreachable"),
        )

        with pytest.raises(OpenCodeUnavailableError, match="unreachable"):
            select_shortlist(
                db_session,
                [item],
                ws,
                run,
                opencode_client=client,
            )

    def test_timeout_error_propagates(self, db_session):
        ws = _make_workspace(db_session, max_articles=10)
        run = _make_run(db_session, ws.id)

        item = _make_item(db_session, ws.id, title="A", final_score=0.9)

        client = _make_enabled_client()
        client.refine_shortlist = MagicMock(  # type: ignore[assignment]
            side_effect=OpenCodeTimeoutError("timed out"),
        )

        with pytest.raises(OpenCodeTimeoutError, match="timed out"):
            select_shortlist(
                db_session,
                [item],
                ws,
                run,
                opencode_client=client,
            )

    def test_response_error_propagates(self, db_session):
        ws = _make_workspace(db_session, max_articles=10)
        run = _make_run(db_session, ws.id)

        item = _make_item(db_session, ws.id, title="A", final_score=0.9)

        client = _make_enabled_client()
        client.refine_shortlist = MagicMock(  # type: ignore[assignment]
            side_effect=OpenCodeResponseError("bad response"),
        )

        with pytest.raises(OpenCodeResponseError, match="bad response"):
            select_shortlist(
                db_session,
                [item],
                ws,
                run,
                opencode_client=client,
            )
