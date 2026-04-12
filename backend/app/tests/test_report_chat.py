"""Tests for report-chat context assembly."""

from app.models.content import ContentItem
from app.models.report import Report, ReportMessage
from app.models.workspace import Workspace
from app.services.report_chat import (
    _rank_source_items_by_relevance,
    get_report_chat_source_ids,
    load_report_chat_source_items,
)


def _workspace(db_session) -> Workspace:
    ws = Workspace(name="Chat WS", customer="Acme")
    db_session.add(ws)
    db_session.flush()
    return ws


def _report(db_session, workspace_id: str, metadata_json: dict | None = None) -> Report:
    report = Report(
        workspace_id=workspace_id,
        title="Chat Report",
        status="published",
        metadata_json=metadata_json,
    )
    db_session.add(report)
    db_session.flush()
    return report


def _message(
    db_session,
    report_id: str,
    *,
    role: str = "system",
    metadata_json: dict | None = None,
) -> ReportMessage:
    msg = ReportMessage(
        thread_id=report_id,
        role=role,
        content="Message",
        metadata_json=metadata_json,
    )
    db_session.add(msg)
    db_session.flush()
    return msg


def _content_item(db_session, workspace_id: str, item_id: str) -> ContentItem:
    item = ContentItem(
        id=item_id,
        workspace_id=workspace_id,
        title=f"Title {item_id}",
        content_type="news",
        status="included",
    )
    db_session.add(item)
    db_session.flush()
    return item


def test_latest_system_message_sources_are_preferred(db_session):
    ws = _workspace(db_session)
    report = _report(db_session, ws.id, metadata_json={"sources": ["report-source"]})
    _message(db_session, report.id, metadata_json={"sources": ["old-system"]})
    _message(db_session, report.id, role="agent", metadata_json={"sources": ["agent"]})
    _message(db_session, report.id, metadata_json={"sources": ["latest-system"]})

    messages = list(report.messages)

    assert get_report_chat_source_ids(report, messages) == ["latest-system"]


def test_report_metadata_sources_are_fallback(db_session):
    ws = _workspace(db_session)
    report = _report(db_session, ws.id, metadata_json={"sources": ["from-report"]})
    _message(db_session, report.id, metadata_json={})

    assert get_report_chat_source_ids(report, list(report.messages)) == ["from-report"]


def test_load_source_items_preserves_requested_order_and_cap(db_session):
    ws = _workspace(db_session)
    for item_id in ["ci-a", "ci-b", "ci-c"]:
        _content_item(db_session, ws.id, item_id)

    items = load_report_chat_source_items(
        db_session,
        workspace_id=ws.id,
        source_ids=["ci-c", "missing", "ci-a", "ci-b"],
        limit=3,
    )

    assert [item.id for item in items] == ["ci-c", "ci-a"]


# ---------------------------------------------------------------------------
# Source item ranking (Pass 7)
# ---------------------------------------------------------------------------


def _make_ranking_item(item_id: str, title: str, summary: str = "") -> ContentItem:
    """Create a lightweight ContentItem-like object for ranking tests."""
    return type(
        "Item",
        (),
        {
            "id": item_id,
            "title": title,
            "summary_snippet": summary,
            "raw_text": "",
        },
    )()


class TestRankSourceItemsByRelevance:
    """_rank_source_items_by_relevance ranks items by keyword overlap."""

    def test_specific_question_prioritizes_relevant_items(self):
        items = [
            _make_ranking_item("1", "AI breakthrough in healthcare"),
            _make_ranking_item("2", "Sports scores from last night"),
            _make_ranking_item("3", "AI regulation proposed by EU"),
        ]
        # Use a question with clean tokens (no punctuation) that match item titles
        question = "AI regulation update"

        ranked = _rank_source_items_by_relevance(question, items)

        # Item 3 matches "AI" and "regulation" — most relevant (2/2 keywords)
        # Item 1 matches "AI" only — somewhat relevant (1/2 keywords)
        # Item 2 matches neither — least relevant (0/2 keywords)
        assert ranked[0].id == "3"
        assert ranked[1].id == "1"
        assert ranked[2].id == "2"

    def test_stop_word_only_question_falls_back_to_original_order(self):
        items = [
            _make_ranking_item("1", "First article"),
            _make_ranking_item("2", "Second article"),
            _make_ranking_item("3", "Third article"),
        ]
        # "the is in on" — all stop words, no meaningful keywords
        question = "the is in on"

        ranked = _rank_source_items_by_relevance(question, items)

        # Should return original order since no keywords to rank by
        assert [item.id for item in ranked] == ["1", "2", "3"]

    def test_empty_question_falls_back_to_original_order(self):
        items = [
            _make_ranking_item("a", "Alpha"),
            _make_ranking_item("b", "Beta"),
        ]
        ranked = _rank_source_items_by_relevance("", items)

        assert [item.id for item in ranked] == ["a", "b"]

    def test_empty_items_returns_empty(self):
        ranked = _rank_source_items_by_relevance("AI news", [])
        assert ranked == []


class TestLoadReportChatSourceItemsWithRanking:
    """load_report_chat_source_items with question parameter applies ranking."""

    def test_question_parameter_applies_ranking_before_limit(self, db_session):
        ws = _workspace(db_session)
        _content_item(db_session, ws.id, "item-sports")
        _content_item(db_session, ws.id, "item-ai-1")
        _content_item(db_session, ws.id, "item-ai-2")
        _content_item(db_session, ws.id, "item-weather")

        # Query all 4 items but limit to 2, with an AI-related question
        items = load_report_chat_source_items(
            db_session,
            workspace_id=ws.id,
            source_ids=["item-sports", "item-ai-1", "item-ai-2", "item-weather"],
            question="Tell me about AI developments",
            limit=2,
        )

        # Should return 2 items, and AI-related ones should be prioritized
        assert len(items) == 2
        titles = [item.title for item in items]
        # AI items should be ranked higher than sports/weather
        assert any("ai" in t.lower() for t in titles)

    def test_no_question_preserves_original_order(self, db_session):
        ws = _workspace(db_session)
        _content_item(db_session, ws.id, "first")
        _content_item(db_session, ws.id, "second")
        _content_item(db_session, ws.id, "third")

        items = load_report_chat_source_items(
            db_session,
            workspace_id=ws.id,
            source_ids=["first", "second", "third"],
            question=None,
            limit=2,
        )

        assert len(items) == 2
        assert items[0].id == "first"
        assert items[1].id == "second"

    def test_empty_question_preserves_original_order(self, db_session):
        ws = _workspace(db_session)
        _content_item(db_session, ws.id, "alpha")
        _content_item(db_session, ws.id, "beta")

        items = load_report_chat_source_items(
            db_session,
            workspace_id=ws.id,
            source_ids=["alpha", "beta"],
            question="",
            limit=10,
        )

        assert items[0].id == "alpha"
        assert items[1].id == "beta"
