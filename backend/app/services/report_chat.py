"""Build grounded report-chat context and call the assistant."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.content import ContentItem
from app.models.report import Report, ReportMessage
from app.services.opencode_client import OpenCodeClient, ReportChatResult

MAX_CHAT_SOURCE_ITEMS = 12
MAX_SOURCE_TEXT_CHARS = 1500
MAX_RECENT_MESSAGES = 12


def generate_report_chat_reply(
    *,
    client: OpenCodeClient,
    question: str,
    report: Report,
    source_items: list[ContentItem],
    recent_messages: list[ReportMessage],
) -> ReportChatResult:
    """Generate a report-thread reply from the current report context."""
    return client.answer_report_question(
        question=question,
        report_context=_report_context(report),
        source_items=[_content_item_context(item) for item in source_items],
        recent_messages=[_message_context(msg) for msg in recent_messages],
    )


def get_report_chat_source_ids(report: Report, messages: list[ReportMessage]) -> list[str]:
    """Return ordered current-report source IDs.

    Prefer the latest generated system report message. Fall back to report
    metadata for legacy/generated threads.
    """
    for msg in reversed(messages):
        if msg.role != "system":
            continue
        source_ids = _metadata_source_ids(msg.metadata_json)
        if source_ids:
            return source_ids
    return _metadata_source_ids(report.metadata_json)


def load_report_chat_source_items(
    db: Session,
    *,
    workspace_id: str,
    source_ids: list[str],
    limit: int = MAX_CHAT_SOURCE_ITEMS,
) -> list[ContentItem]:
    """Load ordered source items for report-chat context."""
    limited_ids = source_ids[:limit]
    if not limited_ids:
        return []

    items_by_id = {
        item.id: item
        for item in (
            db.query(ContentItem)
            .filter(
                ContentItem.workspace_id == workspace_id,
                ContentItem.id.in_(limited_ids),
            )
            .all()
        )
    }
    return [items_by_id[item_id] for item_id in limited_ids if item_id in items_by_id]


def recent_report_chat_messages(
    messages: list[ReportMessage],
    *,
    limit: int = MAX_RECENT_MESSAGES,
) -> list[ReportMessage]:
    """Return the recent conversational messages to include in the prompt."""
    conversational = [msg for msg in messages if msg.role in {"user", "agent"}]
    return conversational[-limit:]


def _metadata_source_ids(metadata: dict | None) -> list[str]:
    raw_sources = (metadata or {}).get("sources")
    if not isinstance(raw_sources, list):
        return []
    return [source_id for source_id in raw_sources if isinstance(source_id, str)]


def _report_context(report: Report) -> dict[str, Any]:
    return {
        "id": report.id,
        "title": report.title,
        "status": report.status,
        "markdown": report.markdown_body,
        "metadata": report.metadata_json or {},
    }


def _content_item_context(item: ContentItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "title": item.title,
        "url": item.url,
        "source_name": item.source_name,
        "content_type": item.content_type,
        "published_at": _iso(item.published_at),
        "summary": item.summary_snippet,
        "text": _cap_text(item.raw_text),
        "inclusion_reason": item.inclusion_reason,
        "final_score": item.final_score,
    }


def _message_context(msg: ReportMessage) -> dict[str, Any]:
    return {
        "id": msg.id,
        "role": msg.role,
        "content": msg.content,
        "created_at": _iso(msg.created_at),
    }


def _cap_text(text: str | None) -> str | None:
    if text is None or len(text) <= MAX_SOURCE_TEXT_CHARS:
        return text
    return text[:MAX_SOURCE_TEXT_CHARS] + "..."


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
