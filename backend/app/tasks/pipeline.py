"""Pipeline functions for feed fetching, content normalization, and report generation."""

import logging
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from app.models.content import ContentItem
from app.models.feed import FeedSource
from app.models.report import Report
from app.models.run import ProcessingRun
from app.models.workspace import Workspace

logger = logging.getLogger(__name__)


def parse_rfc2822(date_str: str) -> datetime | None:
    """Parse an RFC 2822 date string into a timezone-aware datetime."""
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return None


def fetch_feed(feed: FeedSource) -> list[dict]:
    """Fetch and parse a single feed source.

    Returns a list of raw item dicts. Returns an empty list on any error
    so that one bad feed never blocks the entire pipeline.
    """
    try:
        response = httpx.get(feed.url, follow_redirects=True, timeout=10)
        parsed = feedparser.parse(response.text)
        items: list[dict] = []
        for entry in parsed.entries[:20]:  # Limit to 20 items per feed
            items.append(
                {
                    "title": entry.get("title", "Untitled"),
                    "url": entry.get("link", ""),
                    "source_name": parsed.feed.get("title", feed.name),
                    "published_at": parse_rfc2822(
                        entry.get("published", entry.get("updated", ""))
                    ),
                    "author": entry.get("author", ""),
                    "summary": entry.get("summary", ""),
                    "content": (
                        entry.get("content", [{}])[0].get("value", "")
                        if entry.get("content")
                        else ""
                    ),
                }
            )
        return items
    except Exception as exc:
        logger.warning("Failed to fetch feed %s (%s): %s", feed.name, feed.url, exc)
        return []


def normalize_content(
    workspace_id: str, feed: FeedSource, raw_items: list[dict]
) -> list[ContentItem]:
    """Convert raw feed items into ContentItem ORM records.

    The returned items are *not* persisted — the caller is responsible for
    adding them to a session and committing.
    """
    items: list[ContentItem] = []
    for raw in raw_items:
        item = ContentItem(
            workspace_id=workspace_id,
            feed_source_id=feed.id,
            title=raw["title"][:1000],
            url=raw["url"][:2048],
            source_name=raw["source_name"],
            content_type="news" if feed.type == "rss" else "blog",
            published_at=raw.get("published_at"),
            author=raw.get("author"),
            summary_snippet=raw.get("summary", "")[:500],
            raw_text=raw.get("content", ""),
            status="pending",
            local_relevance_score=0.5,  # Default, will be updated by scoring pipeline
        )
        items.append(item)
    return items


def generate_report_stub(
    workspace: Workspace,
    content_items: list[ContentItem],
    run: ProcessingRun,
) -> Report:
    """Generate a simple deterministic report from content items.

    If no items are marked as ``included`` the first five items are used
    as highlights.  The returned ``Report`` is *not* persisted.
    """
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=1)

    included = [c for c in content_items if c.status == "included"] or content_items[:5]

    title = f"{workspace.customer} — Daily News Digest"
    body = f"# {title}\n\n"
    body += f"**Period:** {period_start.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}\n\n"
    body += "## Summary\n\n"
    body += f"We found {len(content_items)} articles. Here are the highlights:\n\n"

    for i, item in enumerate(included[:10], 1):
        body += f"### {i}. {item.title}\n\n"
        body += f"Source: {item.source_name}\n"
        body += f"URL: {item.url}\n\n"
        if item.summary_snippet:
            body += f"{item.summary_snippet}\n\n"
        body += "---\n\n"

    report = Report(
        workspace_id=workspace.id,
        title=title,
        period_start=period_start,
        period_end=now,
        status="published",
        markdown_body=body,
        run_id=run.id,
        published_at=now,
    )
    return report
