"""Build grounded report-chat context and call the assistant."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.content import ContentItem
from app.models.report import Report, ReportMessage
from app.models.workspace import Workspace
from app.services.opencode_client import OpenCodeClient, ReportChatResult

MAX_CHAT_SOURCE_ITEMS = 12
MAX_SOURCE_TEXT_CHARS = 1500
MAX_RECENT_MESSAGES = 12

# Minimal English stop words used for keyword extraction in relevance ranking.
_STOP_WORDS: frozenset[str] = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "and",
        "or",
        "but",
        "not",
        "this",
        "that",
        "it",
        "with",
        "from",
        "by",
        "as",
        "be",
        "has",
        "had",
        "have",
        "do",
        "does",
        "did",
        "will",
        "would",
        "can",
        "could",
        "should",
        "may",
        "might",
    }
)


def generate_report_chat_reply(
    *,
    client: OpenCodeClient,
    question: str,
    report: Report,
    workspace: Workspace | None = None,
    source_items: list[ContentItem],
    recent_messages: list[ReportMessage],
) -> ReportChatResult:
    """Generate a report-thread reply from the current report context."""
    return client.answer_report_question(
        question=question,
        report_context=_report_context(report),
        workspace_context=_workspace_context(workspace) if workspace else None,
        source_items=[_content_item_context(item) for item in source_items],
        recent_messages=[_message_context(msg) for msg in recent_messages],
    )


def get_report_chat_source_ids(
    report: Report, messages: list[ReportMessage]
) -> list[str]:
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


def _extract_keywords(text: str) -> set[str]:
    """Return meaningful keywords from *text* (lowercased, stop words removed)."""
    tokens = set(text.lower().split())
    return tokens - _STOP_WORDS


def _item_text_for_ranking(item: ContentItem) -> str:
    """Build a text blob from item fields used for relevance scoring."""
    parts = [
        item.title or "",
        item.summary_snippet or "",
        (item.raw_text or "")[:500],
    ]
    return " ".join(parts)


def _rank_source_items_by_relevance(
    question: str, items: list[ContentItem]
) -> list[ContentItem]:
    """Rank *items* by keyword overlap with *question*, most relevant first.

    Uses a simple hit-rate: the fraction of question keywords that appear in
    each item's combined ``title + summary_snippet + raw_text[:500]``.
    Ties are broken by original order (Python's sort is stable).

    When *question* has no meaningful keywords the original list is returned
    unchanged.
    """
    keywords = _extract_keywords(question)
    if not keywords:
        return items

    def _score(item: ContentItem) -> float:
        item_tokens = set(_item_text_for_ranking(item).lower().split())
        if not item_tokens:
            return 0.0
        return len(keywords & item_tokens) / len(keywords)

    return sorted(items, key=_score, reverse=True)


def load_report_chat_source_items(
    db: Session,
    *,
    workspace_id: str,
    source_ids: list[str],
    question: str | None = None,
    limit: int = MAX_CHAT_SOURCE_ITEMS,
) -> list[ContentItem]:
    """Load ordered source items for report-chat context.

    When *question* contains meaningful keywords, all source items are
    fetched and ranked by relevance before the *limit* is applied so that
    the most relevant items are kept.  Without a question (or when the
    question has no meaningful keywords), the original insertion-order
    behaviour is preserved.
    """
    if not source_ids:
        return []

    # Determine whether we should rank items by relevance.
    keywords = _extract_keywords(question) if question else set()
    should_rank = bool(keywords)

    # When ranking, query all source IDs first so we can pick the best ones.
    ids_to_query = source_ids if should_rank else source_ids[:limit]

    items_by_id = {
        item.id: item
        for item in (
            db.query(ContentItem)
            .filter(
                ContentItem.workspace_id == workspace_id,
                ContentItem.id.in_(ids_to_query),
            )
            .all()
        )
    }

    items = [items_by_id[item_id] for item_id in ids_to_query if item_id in items_by_id]

    if should_rank and question:
        items = _rank_source_items_by_relevance(question, items)

    return items[:limit]


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


def _workspace_context(workspace: Workspace) -> dict[str, Any]:
    ctx: dict[str, Any] = {
        "name": workspace.name,
        "customer": workspace.customer,
    }
    if workspace.profile:
        p = workspace.profile
        ctx["business_name"] = p.business_name
        ctx["description"] = p.description
        ctx["products"] = p.products or []
        ctx["competitors"] = p.competitors or []
        ctx["priority_themes"] = p.priority_themes or []
    return ctx


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
