"""Reusable pipeline step helpers."""

from __future__ import annotations

import calendar
import hashlib
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING

import feedparser
import httpx

from app.models.content import ContentItem
from app.models.feed import FeedSource
from app.services.dedup import normalize_url

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Entry-normalisation helpers
# ---------------------------------------------------------------------------


def _strip_html_tags(text: str) -> str:
    """Remove HTML tags from *text*, returning plain text."""
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", "", text)
    # Collapse runs of whitespace into a single space
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _struct_time_to_dt(
    struct: time.struct_time | None,
) -> datetime | None:
    """Convert a feedparser ``time.struct_time`` to a timezone-aware UTC datetime."""
    if struct is None:
        return None
    try:
        ts = calendar.timegm(struct)
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _extract_url(entry) -> str:
    """Extract and normalise the canonical URL from a feedparser entry."""
    raw_url = entry.get("link") or entry.get("id") or ""
    return normalize_url(raw_url)


def _extract_author(entry) -> str | None:
    """Extract author name from a feedparser entry, trying multiple sources."""
    if entry.get("author"):
        return entry.get("author")
    if entry.get("dc:creator"):
        return entry.get("dc:creator")
    if entry.get("dc_creator"):
        return entry.get("dc_creator")
    authors = entry.get("authors")
    if authors and isinstance(authors, (list, tuple)) and len(authors) > 0:
        first = authors[0]
        name = (
            first.get("name")
            if isinstance(first, dict)
            else getattr(first, "name", None)
        )
        if name:
            return name
    return None


def _extract_published_at(entry) -> datetime | None:
    """Extract publication timestamp from a feedparser entry using multiple strategies."""
    # Try string-based parsing first (feedparser's published / updated)
    for field in ("published", "updated"):
        date_str = entry.get(field)
        if date_str:
            dt = parse_rfc2822(date_str)
            if dt:
                return dt
    # Fall back to pre-parsed struct_time fields
    for field in ("published_parsed", "updated_parsed"):
        struct = entry.get(field)
        if struct:
            dt = _struct_time_to_dt(struct)
            if dt:
                return dt
    return None


def _extract_summary(entry) -> str:
    """Extract summary, stripping HTML tags if present."""
    return _strip_html_tags(entry.get("summary", ""))


def _extract_raw_text(entry) -> str:
    """Extract full text/body content from a feedparser entry."""
    content = entry.get("content")
    if content and isinstance(content, (list, tuple)) and len(content) > 0:
        raw = content[0]
        value = (
            raw.get("value") if isinstance(raw, dict) else getattr(raw, "value", None)
        )
        if value:
            return _strip_html_tags(value)
    # Fallback to summary or description
    return _strip_html_tags(entry.get("summary", "") or entry.get("description", ""))


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
                "url": _extract_url(entry),
                "source_name": source_title,
                "published_at": _extract_published_at(entry),
                "author": _extract_author(entry),
                "summary": _extract_summary(entry),
                "raw_text": _extract_raw_text(entry),
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
    workspace_id: str,
    feed: FeedSource,
    raw_items: list[dict],
    *,
    db: Session | None = None,
) -> tuple[list[ContentItem], int]:
    """Convert raw feed items into ContentItem ORM records.

    When *db* is provided, entries whose ``source_entry_id`` already exists
    in the database for the same *workspace_id* are skipped (idempotent
    re-ingestion).  The ``source_entry_id`` is also set on each newly
    created ``ContentItem``.

    Returns:
        A ``(content_items, skipped_count)`` tuple.  When *db* is ``None``,
        ``skipped_count`` is always ``0``.
    """
    skipped_count = 0

    # Pre-load existing source_entry_ids for the workspace when db is provided.
    existing_ids: set[str] | None = None
    if db is not None:
        rows = (
            db.query(ContentItem.source_entry_id)
            .filter(
                ContentItem.workspace_id == workspace_id,
                ContentItem.source_entry_id.isnot(None),
            )
            .all()
        )
        existing_ids = {row[0] for row in rows if row[0] is not None}

    items: list[ContentItem] = []
    for raw in raw_items:
        # Compute source_entry_id for deduplication.
        entry_id = compute_source_entry_id(raw)

        # Skip if already imported (only when db is provided).
        if db is not None and existing_ids is not None and entry_id is not None:
            if entry_id in existing_ids:
                skipped_count += 1
                logger.debug("Skipping duplicate entry (source_entry_id=%s)", entry_id)
                continue

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
            raw_text=raw.get("raw_text", ""),
            status="pending",
            local_relevance_score=0.5,
            source_entry_id=entry_id,
        )
        items.append(item)

    return items, skipped_count


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
