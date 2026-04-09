"""Tests for report-chat context assembly."""

from app.models.content import ContentItem
from app.models.report import Report, ReportMessage
from app.models.workspace import Workspace
from app.services.report_chat import (
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
