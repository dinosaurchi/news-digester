"""Reusable pipeline step helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from app.models.content import ContentItem
from app.models.feed import FeedSource

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeedValidationResult:
    """Result of fetching/parsing a configured feed source."""

    success: bool
    articles_found: int
    source_title: str
    error: str | None = None


def parse_rfc2822(date_str: str) -> datetime | None:
    """Parse an RFC 2822 date string into a timezone-aware datetime."""
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return None


def fetch_feed(feed: FeedSource) -> list[dict]:
    """Fetch and parse a single feed source."""
    try:
        response = httpx.get(feed.url, follow_redirects=True, timeout=10)
        parsed = feedparser.parse(response.text)
        items: list[dict] = []
        for entry in parsed.entries[:20]:
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


def validate_feed_source(feed: FeedSource) -> FeedValidationResult:
    """Fetch a feed URL and validate that it returns parseable feed entries."""
    try:
        response = httpx.get(feed.url, follow_redirects=True, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return FeedValidationResult(
            success=False,
            articles_found=0,
            source_title=feed.name,
            error=f"Fetch failed: {exc}",
        )

    parsed = feedparser.parse(response.text)
    entries = list(parsed.entries)
    source_title = parsed.feed.get("title", feed.name)

    if parsed.bozo:
        error = getattr(parsed, "bozo_exception", None)
        return FeedValidationResult(
            success=False,
            articles_found=len(entries),
            source_title=source_title,
            error=f"Feed parse failed: {error}",
        )

    if not entries:
        return FeedValidationResult(
            success=False,
            articles_found=0,
            source_title=source_title,
            error="Feed parsed successfully but contained no entries.",
        )

    return FeedValidationResult(
        success=True,
        articles_found=len(entries),
        source_title=source_title,
    )


def normalize_content(
    workspace_id: str, feed: FeedSource, raw_items: list[dict]
) -> list[ContentItem]:
    """Convert raw feed items into ContentItem ORM records."""
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
            local_relevance_score=0.5,
        )
        items.append(item)
    return items
