"""Reusable pipeline step helpers."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from app.models.content import ContentItem
from app.models.feed import FeedSource
from app.services.dedup import normalize_url

logger = logging.getLogger(__name__)


@dataclass
class FeedFetchResult:
    """Structured result from fetching a single feed source."""

    success: bool
    entries: list[dict]
    error: str | None
    source_title: str


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


def fetch_feed(feed: FeedSource) -> FeedFetchResult:
    """Fetch and parse a single feed source.

    Returns a :class:`FeedFetchResult` that distinguishes between an empty
    feed (``success=True, entries=[]``) and a fetch/parse error
    (``success=False, entries=[], error="..."``).
    """
    # --- HTTP fetch ---
    try:
        response = httpx.get(feed.url, follow_redirects=True, timeout=10)
    except Exception as exc:
        logger.warning("Failed to fetch feed %s (%s): %s", feed.name, feed.url, exc)
        return FeedFetchResult(
            success=False,
            entries=[],
            error=f"Fetch failed: {exc}",
            source_title=feed.name,
        )

    # --- Parse ---
    parsed = feedparser.parse(response.text)
    source_title = parsed.feed.get("title", feed.name)

    if parsed.bozo:
        bozo_exc = getattr(parsed, "bozo_exception", None)
        logger.warning(
            "Feed parse error for %s (%s): %s", feed.name, feed.url, bozo_exc
        )
        return FeedFetchResult(
            success=False,
            entries=[],
            error=f"Feed parse failed: {bozo_exc}",
            source_title=source_title,
        )

    # --- Extract entries ---
    items: list[dict] = []
    for entry in parsed.entries[:20]:
        items.append(
            {
                "title": entry.get("title", "Untitled"),
                "url": entry.get("link", ""),
                "source_name": source_title,
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

    return FeedFetchResult(
        success=True,
        entries=items,
        error=None,
        source_title=source_title,
    )


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


def compute_source_entry_id(raw_item: dict) -> str | None:
    """Compute a deterministic fingerprint for a raw feed entry.

    Produces a stable identity string suitable for deduplication and
    idempotent re-ingestion of feed items.

    Resolution strategy:

    1. **URL-based identity** — If the entry has a non-empty ``link``
       (raw feedparser) or ``url`` (processed dict), the value is
       normalized via :func:`app.services.dedup.normalize_url` and
       returned.
    2. **Composite hash** — When no usable URL is present, a SHA-256
       hex digest is computed from the concatenation of ``title``,
       ``source_name``, and ``published_at`` (or ``published`` /
       ``updated`` for raw entries).
    3. **None** — Returned when none of the required fields are
       available.

    Args:
        raw_item: A raw feed entry dict.  Accepts both raw feedparser
            entries (with ``link``, ``published``, ``updated`` keys) and
            processed dicts produced by :func:`fetch_feed` (with ``url``,
            ``source_name``, ``published_at`` keys).

    Returns:
        A normalized URL string, a SHA-256 hex digest, or ``None``.
    """
    # 1. Prefer URL-based identity.
    link = raw_item.get("link") or raw_item.get("url")
    if link:
        normalized = normalize_url(link)
        if normalized:
            return normalized

    # 2. Fall back to composite hash of title + source_name + published_at.
    title = raw_item.get("title")
    source_name = raw_item.get("source_name")
    # Accept both datetime objects and raw date strings.
    published_at = (
        raw_item.get("published_at")
        or raw_item.get("published")
        or raw_item.get("updated")
    )

    if title and source_name and published_at is not None:
        composite = f"{title}|{source_name}|{published_at}"
        return hashlib.sha256(composite.encode("utf-8")).hexdigest()

    # 3. Insufficient data.
    return None
