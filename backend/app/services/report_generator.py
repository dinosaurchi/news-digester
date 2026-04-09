"""Report generation module.

Replaces the deterministic stub report generation with a real report
generation path that supports both LLM-powered and template-based
markdown output.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.content import ContentItem
from app.models.report import Report, ReportMessage
from app.models.run import ProcessingRun
from app.models.workspace import Workspace
from app.services.opencode_client import OpenCodeClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_report(
    db: Session,
    workspace: Workspace,
    shortlist_items: list[ContentItem],
    run: ProcessingRun,
    *,
    opencode_client: OpenCodeClient | None = None,
) -> Report:
    """Generate a report from shortlisted content items.

    Steps:
    1. Assemble structured report input (title, period, item data).
    2. Generate report markdown via LLM or deterministic template.
    3. Create and persist a ``Report`` record linked to workspace and run.
    4. Create and persist a ``ReportMessage`` linked to the report via thread_id.
    5. Return the ``Report`` object.

    Parameters
    ----------
    db:
        SQLAlchemy session.
    workspace:
        The workspace the report belongs to.
    shortlist_items:
        ContentItem ORM objects selected for inclusion in the report.
    run:
        The current processing run.
    opencode_client:
        Optional LLM client.  When provided, the report markdown is generated
        by the LLM.  When ``None``, a deterministic template is used.

    Returns
    -------
    The persisted ``Report`` object (with ``id`` assigned).

    Raises
    ------
    OpenCodeUnavailableError, OpenCodeTimeoutError, OpenCodeResponseError:
        If *opencode_client* is provided and the LLM call fails.  These
        propagate to the caller; there is **no** silent fallback.
    """
    now = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # 0. Load feedback context for traceability
    # ------------------------------------------------------------------
    feedback_context = _load_feedback_context(db, workspace.id)

    # ------------------------------------------------------------------
    # 1. Assemble structured report input
    # ------------------------------------------------------------------
    title, period_start, period_end, items_data = _assemble_input(
        workspace, shortlist_items, now
    )

    # ------------------------------------------------------------------
    # 2. Generate report markdown
    # ------------------------------------------------------------------
    if opencode_client is not None:
        markdown = _generate_via_llm(
            opencode_client, workspace, items_data, period_start, period_end
        )
    else:
        markdown = _generate_deterministic(title, period_start, period_end, items_data)

    # ------------------------------------------------------------------
    # 3. Create Report record
    # ------------------------------------------------------------------
    source_ids = [item.id for item in shortlist_items]
    metadata: dict[str, Any] = {"sources": source_ids}
    if feedback_context:
        metadata["feedback_context"] = feedback_context

    report = Report(
        workspace_id=workspace.id,
        title=title,
        period_start=period_start,
        period_end=period_end,
        status="published",
        markdown_body=markdown,
        run_id=run.id,
        published_at=now,
        metadata_json=metadata,
    )
    db.add(report)
    db.flush()  # assign report.id before creating the message

    # ------------------------------------------------------------------
    # 4. Create ReportMessage
    # ------------------------------------------------------------------
    message = ReportMessage(
        thread_id=report.id,
        role="system",
        content=markdown,
        metadata_json={
            "sources": source_ids,
            "reportId": report.id,
        },
    )
    db.add(message)
    db.flush()

    return report


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_feedback_context(db: Session, workspace_id: str) -> dict[str, Any] | None:
    """Load feedback influence summary for a workspace.

    Returns a dict with keys ``topics_influenced``, ``sources_influenced``,
    and ``feedback_event_count``, or ``None`` when no feedback data exists.
    """
    topic_weights: dict[str, float] = {}
    source_weights: dict[str, float] = {}
    feedback_event_count: int = 0

    try:
        from app.models.preferences import TopicPreference, SourcePreference

        topic_prefs = (
            db.query(TopicPreference)
            .filter(TopicPreference.workspace_id == workspace_id)
            .all()
        )
        for tp in topic_prefs:
            topic_weights[tp.topic] = topic_weights.get(tp.topic, 0.0) + tp.weight

        source_prefs = (
            db.query(SourcePreference)
            .filter(SourcePreference.workspace_id == workspace_id)
            .all()
        )
        for sp in source_prefs:
            source_weights[sp.source_name] = (
                source_weights.get(sp.source_name, 0.0) + sp.weight
            )

    except Exception:
        logger.debug(
            "Could not load preference models for feedback context", exc_info=True
        )

    try:
        from app.models.report import FeedbackEvent

        feedback_event_count = (
            db.query(FeedbackEvent)
            .filter(FeedbackEvent.workspace_id == workspace_id)
            .count()
        )
    except Exception:
        logger.debug("Could not load feedback event count", exc_info=True)

    # Return None when there is absolutely no feedback data
    if not topic_weights and not source_weights and feedback_event_count == 0:
        return None

    topics_influenced: list[dict[str, Any]] = []
    for topic, weight in topic_weights.items():
        topics_influenced.append(
            {
                "topic": topic,
                "weight": weight,
                "direction": "positive" if weight > 0 else "negative",
            }
        )

    sources_influenced: list[dict[str, Any]] = []
    for source, weight in source_weights.items():
        sources_influenced.append(
            {
                "source": source,
                "weight": weight,
                "direction": "positive" if weight > 0 else "negative",
            }
        )

    return {
        "topics_influenced": topics_influenced,
        "sources_influenced": sources_influenced,
        "feedback_event_count": feedback_event_count,
    }


def _assemble_input(
    workspace: Workspace,
    shortlist_items: list[ContentItem],
    now: datetime,
) -> tuple[str, datetime, datetime, list[dict[str, Any]]]:
    """Build structured data for report generation.

    Returns (title, period_start, period_end, items_data).
    """
    # Determine period from shortlist item dates
    published_dates = [
        item.published_at for item in shortlist_items if item.published_at is not None
    ]

    if published_dates:
        period_start = min(published_dates)
        period_end = max(published_dates)
    else:
        period_start = now
        period_end = now

    title = f"{workspace.customer} — Daily News Digest"

    items_data: list[dict[str, Any]] = []
    for item in shortlist_items:
        items_data.append(
            {
                "id": item.id,
                "title": item.title,
                "url": item.url,
                "summary": item.summary_snippet or "",
                "source": item.source_name or "",
                "published_at": (
                    item.published_at.isoformat() if item.published_at else None
                ),
                "score": item.final_score,
            }
        )

    return title, period_start, period_end, items_data


def _generate_via_llm(
    client: OpenCodeClient,
    workspace: Workspace,
    items_data: list[dict[str, Any]],
    period_start: datetime,
    period_end: datetime,
) -> str:
    """Generate report markdown using the LLM client.

    **Exceptions from the LLM call are not caught** — they propagate to the
    caller so the pipeline can mark the run as failed.
    """
    workspace_context: dict[str, Any] = {
        "workspace_id": workspace.id,
        "name": workspace.name,
        "customer": workspace.customer,
    }
    if workspace.profile:
        workspace_context["priority_themes"] = workspace.profile.priority_themes or []
        workspace_context["competitors"] = workspace.profile.competitors or []
        workspace_context["excluded_topics"] = workspace.profile.excluded_topics or []

    period: dict[str, str] = {
        "start": period_start.isoformat(),
        "end": period_end.isoformat(),
    }

    result = client.generate_report_markdown(items_data, workspace_context, period)
    return result.markdown


def _generate_deterministic(
    title: str,
    period_start: datetime,
    period_end: datetime,
    items_data: list[dict[str, Any]],
) -> str:
    """Generate report markdown from a deterministic template."""
    period_str = (
        f"{period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}"
    )

    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Period**: {period_str}")
    lines.append("")

    if not items_data:
        lines.append("## Summary")
        lines.append("")
        lines.append("No items found for this reporting period.")
        return "\n".join(lines)

    # Top Highlights
    lines.append("## Top Highlights")
    lines.append("")
    for i, item in enumerate(items_data, 1):
        summary = item.get("summary", "")
        url = item.get("url", "")
        item_title = item.get("title", "Untitled")
        link = f"[source]({url})" if url else ""
        lines.append(f"{i}. {item_title} — {summary} {link}")
    lines.append("")

    # Source Details
    lines.append("## Source Details")
    lines.append("")
    for item in items_data:
        item_title = item.get("title", "Untitled")
        date = item.get("published_at", "Unknown")
        score = item.get("score")
        summary = item.get("summary", "")
        url = item.get("url", "")

        lines.append(f"### {item_title}")
        lines.append(f"Published: {date} | Score: {score}")
        lines.append("")
        lines.append(summary)
        lines.append("")
        if url:
            lines.append(f"[Read more]({url})")
            lines.append("")

    return "\n".join(lines)
