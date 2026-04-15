"""Tests for pipeline helper functions."""

import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.models.content import ContentItem
from app.services.pipeline_steps import (
    FeedFetchResult,
    _extract_author,
    _extract_published_at,
    _extract_raw_text,
    _extract_summary,
    _extract_url,
    _pick_best_url,
    _strip_html_tags,
    _struct_time_to_dt,
    compute_source_entry_id,
    enrich_article_body,
    fetch_feed,
    normalize_content,
    parse_rfc2822,
    resolve_news_url,
)


class TestParseRfc2822:
    """parse_rfc2822 date helper."""

    def test_parse_rfc2822_valid(self):
        """Valid RFC 2822 date string is parsed correctly."""
        result = parse_rfc2822("Wed, 20 Mar 2024 08:00:00 +0000")
        assert result is not None
        assert result.year == 2024
        assert result.month == 3
        assert result.day == 20

    def test_parse_rfc2822_iso_format(self):
        """ISO-format date string that feedparser may return."""
        result = parse_rfc2822("2024-03-20T08:00:00Z")
        # parsedate_to_datetime may or may not handle ISO — we just need it not to crash
        # The function returns None on failure, which is acceptable
        assert result is None or isinstance(result, datetime)

    def test_parse_rfc2822_invalid(self):
        """Invalid / empty string returns None."""
        assert parse_rfc2822("") is None
        assert parse_rfc2822("not-a-date") is None
        assert parse_rfc2822("abc123") is None


class TestNormalizeContent:
    """normalize_content produces ContentItem records from raw dicts."""

    def test_normalize_content_basic(self):
        """Raw feed items are converted to ContentItem objects."""

        # Build a lightweight FeedSource-like object (no DB needed)
        class FakeFeed:
            id = "feed-test"
            type = "rss"
            name = "Test Feed"

        raw_items = [
            {
                "title": "Article One",
                "url": "https://example.com/1",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "A short summary",
                "raw_text": "Full content here",
            },
        ]

        items, skipped = normalize_content("ws-1", FakeFeed(), raw_items)
        assert len(items) == 1
        assert skipped == 0

        item = items[0]
        assert item.workspace_id == "ws-1"
        assert item.feed_source_id == "feed-test"
        assert item.title == "Article One"
        assert item.url == "https://example.com/1"
        assert item.source_name == "Example"
        assert item.content_type == "news"  # type=rss → news
        assert item.status == "pending"
        assert item.local_relevance_score == 0.5

    def test_normalize_content_blog_type(self):
        """Feed type 'blog' produces content_type='blog'."""

        class FakeFeed:
            id = "feed-blog"
            type = "blog"
            name = "Blog Feed"

        raw_items = [
            {
                "title": "Blog Post",
                "url": "https://blog.example.com/post",
                "source_name": "My Blog",
                "published_at": None,
                "author": "",
                "summary": "",
                "raw_text": "",
            },
        ]

        items, skipped = normalize_content("ws-1", FakeFeed(), raw_items)
        assert items[0].content_type == "blog"

    def test_normalize_content_empty(self):
        """Empty raw items list produces empty ContentItem list."""

        class FakeFeed:
            id = "feed-empty"
            type = "rss"
            name = "Empty"

        items, skipped = normalize_content("ws-1", FakeFeed(), [])
        assert items == []
        assert skipped == 0

    def test_normalize_content_truncates_long_fields(self):
        """Title and URL are truncated to model column limits."""

        class FakeFeed:
            id = "feed-long"
            type = "rss"
            name = "Long Feed"

        raw_items = [
            {
                "title": "X" * 2000,
                "url": "https://example.com/" + "a" * 3000,
                "source_name": "Source",
                "published_at": None,
                "author": "",
                "summary": "S" * 1000,
                "raw_text": "",
            },
        ]

        items, skipped = normalize_content("ws-1", FakeFeed(), raw_items)
        assert len(items[0].title) <= 1000
        assert len(items[0].url) <= 2048
        assert len(items[0].summary_snippet) <= 500

    def test_normalize_content_sets_source_entry_id(self):
        """source_entry_id is set on ContentItem when available."""

        class FakeFeed:
            id = "feed-test"
            type = "rss"
            name = "Test Feed"

        raw_items = [
            {
                "title": "Article One",
                "url": "https://example.com/1",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "A short summary",
                "raw_text": "Full content here",
            },
        ]

        items, skipped = normalize_content("ws-1", FakeFeed(), raw_items)
        assert skipped == 0
        assert items[0].source_entry_id is not None
        # Should be the normalized URL
        assert "example.com" in items[0].source_entry_id.lower()

    def test_normalize_content_idempotent_with_db(self, db_session):
        """When db is provided, existing entries are skipped."""

        # First, create an existing ContentItem with a source_entry_id
        existing = ContentItem(
            workspace_id="ws-1",
            feed_source_id="feed-test",
            title="Article One",
            url="https://example.com/1",
            source_name="Example",
            content_type="news",
            published_at=datetime(2024, 3, 20, tzinfo=timezone.utc),
            status="pending",
            local_relevance_score=0.5,
            source_entry_id="https://example.com/1",
        )
        db_session.add(existing)
        db_session.commit()

        class FakeFeed:
            id = "feed-test"
            type = "rss"
            name = "Test Feed"

        raw_items = [
            {
                "title": "Article One",
                "url": "https://example.com/1",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "A short summary",
                "raw_text": "Full content here",
            },
            {
                "title": "Article Two",
                "url": "https://example.com/2",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 21, tzinfo=timezone.utc),
                "author": "Bob",
                "summary": "Another summary",
                "raw_text": "More content",
            },
        ]

        items, skipped = normalize_content("ws-1", FakeFeed(), raw_items, db=db_session)
        assert skipped == 1  # Article One was skipped
        assert len(items) == 1  # Only Article Two
        assert items[0].title == "Article Two"

    def test_normalize_content_no_skip_when_db_is_none(self):
        """When db is None, no deduplication occurs."""

        class FakeFeed:
            id = "feed-test"
            type = "rss"
            name = "Test Feed"

        raw_items = [
            {
                "title": "Article One",
                "url": "https://example.com/1",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "A short summary",
                "raw_text": "Full content here",
            },
            {
                "title": "Article Two",
                "url": "https://example.com/1",  # Same URL (duplicate)
                "source_name": "Example",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "A short summary",
                "raw_text": "Full content here",
            },
        ]

        items, skipped = normalize_content("ws-1", FakeFeed(), raw_items)
        assert skipped == 0  # No skipping when db is None
        assert len(items) == 2  # Both items returned


class TestStripHtmlTags:
    """_strip_html_tags helper."""

    def test_plain_text_unchanged(self):
        assert _strip_html_tags("Hello world") == "Hello world"

    def test_strips_tags(self):
        assert _strip_html_tags("<p>Hello</p>") == "Hello"

    def test_strips_nested_tags(self):
        assert _strip_html_tags("<div><b>Bold</b> text</div>") == "Bold text"

    def test_collapses_whitespace(self):
        assert _strip_html_tags("<p>foo</p>  <p>bar</p>") == "foo bar"

    def test_empty_and_none(self):
        assert _strip_html_tags("") == ""
        assert _strip_html_tags(None) == ""  # type: ignore[arg-type]


class TestStructTimeToDt:
    """_struct_time_to_dt helper."""

    def test_valid_struct_time(self):
        struct = time.gmtime(1710921600)  # 2024-03-20 08:00:00 UTC
        result = _struct_time_to_dt(struct)
        assert result is not None
        assert result.year == 2024
        assert result.month == 3
        assert result.day == 20
        assert result.tzinfo == timezone.utc

    def test_none_returns_none(self):
        assert _struct_time_to_dt(None) is None


class TestExtractUrl:
    """_extract_url helper."""

    def test_link_with_tracking_params(self):
        entry = {"link": "https://example.com/article?utm_source=tw&ref=news"}
        result = _extract_url(entry)
        # Tracking params should be stripped
        assert "utm_source" not in result
        assert "ref" not in result

    def test_id_fallback(self):
        entry = {"id": "https://example.com/42"}
        result = _extract_url(entry)
        assert result == "https://example.com/42"

    def test_empty_entry(self):
        entry = {}
        result = _extract_url(entry)
        assert result == ""

    def test_normalizes_hostname(self):
        entry = {"link": "https://EXAMPLE.COM/path"}
        result = _extract_url(entry)
        assert "example.com" in result.lower()


class TestExtractAuthor:
    """_extract_author helper."""

    def test_author_field(self):
        entry = {"author": "Jane Doe"}
        assert _extract_author(entry) == "Jane Doe"

    def test_dc_creator(self):
        entry = {"dc:creator": "John Smith"}
        assert _extract_author(entry) == "John Smith"

    def test_dc_creator_underscore(self):
        entry = {"dc_creator": "Bob Lee"}
        assert _extract_author(entry) == "Bob Lee"

    def test_authors_list(self):
        entry = {"authors": [{"name": "Alice"}]}
        assert _extract_author(entry) == "Alice"

    def test_priority_author_over_authors_list(self):
        entry = {"author": "Jane", "authors": [{"name": "Alice"}]}
        assert _extract_author(entry) == "Jane"

    def test_none_when_missing(self):
        entry = {}
        assert _extract_author(entry) is None

    def test_none_when_authors_empty(self):
        entry = {"authors": []}
        assert _extract_author(entry) is None


class TestExtractPublishedAt:
    """_extract_published_at helper."""

    def test_published_string(self):
        entry = {"published": "Wed, 20 Mar 2024 08:00:00 +0000"}
        result = _extract_published_at(entry)
        assert result is not None
        assert result.year == 2024

    def test_updated_fallback(self):
        entry = {"updated": "Wed, 20 Mar 2024 08:00:00 +0000"}
        result = _extract_published_at(entry)
        assert result is not None
        assert result.year == 2024

    def test_published_parsed_fallback(self):
        entry = {"published_parsed": time.gmtime(1710921600)}
        result = _extract_published_at(entry)
        assert result is not None
        assert result.year == 2024
        assert result.tzinfo == timezone.utc

    def test_updated_parsed_fallback(self):
        entry = {"updated_parsed": time.gmtime(1710921600)}
        result = _extract_published_at(entry)
        assert result is not None
        assert result.year == 2024

    def test_none_when_missing(self):
        entry = {}
        assert _extract_published_at(entry) is None

    def test_published_takes_priority_over_updated(self):
        entry = {
            "published": "Wed, 20 Mar 2024 08:00:00 +0000",
            "updated": "Wed, 21 Mar 2024 08:00:00 +0000",
        }
        result = _extract_published_at(entry)
        assert result is not None
        assert result.day == 20  # published, not updated (21st)


class TestExtractSummary:
    """_extract_summary helper."""

    def test_plain_summary(self):
        entry = {"summary": "A plain summary"}
        assert _extract_summary(entry) == "A plain summary"

    def test_html_summary_stripped(self):
        entry = {"summary": "<p>A <b>bold</b> summary</p>"}
        assert _extract_summary(entry) == "A bold summary"

    def test_empty_entry(self):
        entry = {}
        assert _extract_summary(entry) == ""


class TestExtractRawText:
    """_extract_raw_text helper."""

    def test_content_value(self):
        entry = {"content": [{"value": "Full body text"}]}
        assert _extract_raw_text(entry) == "Full body text"

    def test_content_value_html_stripped(self):
        entry = {"content": [{"value": "<div>Full <em>body</em> text</div>"}]}
        assert _extract_raw_text(entry) == "Full body text"

    def test_fallback_to_summary(self):
        entry = {"summary": "Fallback summary"}
        assert _extract_raw_text(entry) == "Fallback summary"

    def test_fallback_to_description(self):
        entry = {"description": "Fallback description"}
        assert _extract_raw_text(entry) == "Fallback description"

    def test_content_takes_priority_over_summary(self):
        entry = {
            "content": [{"value": "Body content"}],
            "summary": "Summary text",
        }
        assert _extract_raw_text(entry) == "Body content"

    def test_empty_entry(self):
        entry = {}
        assert _extract_raw_text(entry) == ""


# ---------------------------------------------------------------------------
# Article enrichment tests
# ---------------------------------------------------------------------------


class TestEnrichArticleBodySuccess:
    """enrich_article_body successfully extracts text from an HTML page."""

    @patch("app.services.pipeline_steps.trafilatura")
    def test_returns_extracted_text(self, mock_trafilatura):
        """Returns non-empty extracted text from a valid HTML response."""
        mock_trafilatura.extract.return_value = "This is extracted article text."
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.text = (
            "<html><body><p>This is extracted article text.</p></body></html>"
        )
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.pipeline_steps.httpx.get", return_value=mock_response):
            result = enrich_article_body("https://example.com/article")

        assert result == "This is extracted article text."
        mock_trafilatura.extract.assert_called_once()

    @patch("app.services.pipeline_steps.trafilatura")
    def test_trafilatura_is_called(self, mock_trafilatura):
        """trafilatura.extract is called with the response text."""
        mock_trafilatura.extract.return_value = "Some text"
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.text = "<html><body>Content</body></html>"
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.pipeline_steps.httpx.get", return_value=mock_response):
            enrich_article_body("https://example.com/article")

        mock_trafilatura.extract.assert_called_once_with(
            "<html><body>Content</body></html>"
        )


class TestEnrichArticleBodyFailure:
    """enrich_article_body returns None on errors and does not raise."""

    def test_returns_none_on_http_timeout(self):
        """HTTP timeout returns None without raising."""
        with patch(
            "app.services.pipeline_steps.httpx.get",
            side_effect=httpx.TimeoutException("timeout"),
        ):
            result = enrich_article_body("https://example.com/article")

        assert result is None

    def test_returns_none_on_http_error(self):
        """HTTP error (e.g. 404) returns None without raising."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )

        with patch("app.services.pipeline_steps.httpx.get", return_value=mock_response):
            result = enrich_article_body("https://example.com/article")

        assert result is None

    def test_returns_none_on_connection_error(self):
        """Network connection error returns None without raising."""
        with patch(
            "app.services.pipeline_steps.httpx.get",
            side_effect=httpx.ConnectError("connection refused"),
        ):
            result = enrich_article_body("https://example.com/article")

        assert result is None

    @patch("app.services.pipeline_steps.trafilatura")
    def test_returns_none_on_trafilatura_failure(self, mock_trafilatura):
        """trafilatura exception returns None without raising."""
        mock_trafilatura.extract.side_effect = RuntimeError("extraction failed")
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.text = "<html><body>Content</body></html>"
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.pipeline_steps.httpx.get", return_value=mock_response):
            result = enrich_article_body("https://example.com/article")

        assert result is None

    def test_returns_none_for_non_html_content(self):
        """Non-HTML content-type returns None."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.pipeline_steps.httpx.get", return_value=mock_response):
            result = enrich_article_body("https://example.com/doc.pdf")

        assert result is None

    @patch("app.services.pipeline_steps.trafilatura")
    def test_returns_none_when_trafilatura_returns_empty(self, mock_trafilatura):
        """When trafilatura returns None/empty, returns None."""
        mock_trafilatura.extract.return_value = None
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.text = "<html><body></body></html>"
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.pipeline_steps.httpx.get", return_value=mock_response):
            result = enrich_article_body("https://example.com/article")

        assert result is None


class TestEnrichArticleBodyLengthCap:
    """enrich_article_body caps extracted text to ARTICLE_BODY_MAX_LENGTH."""

    @patch("app.services.pipeline_steps.trafilatura")
    def test_text_capped_to_max_length(self, mock_trafilatura):
        """Extracted text longer than ARTICLE_BODY_MAX_LENGTH is truncated."""
        # Generate text that exceeds the default max length of 10000 chars
        long_text = "A" * 15000
        mock_trafilatura.extract.return_value = long_text

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.text = "<html><body>Long content</body></html>"
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.pipeline_steps.httpx.get", return_value=mock_response):
            result = enrich_article_body("https://example.com/article")

        assert result is not None
        assert len(result) == 10000  # capped to default max
        assert result == "A" * 10000

    @patch("app.services.pipeline_steps.trafilatura")
    def test_short_text_unchanged(self, mock_trafilatura):
        """Extracted text shorter than max length is not truncated."""
        short_text = "Short article text."
        mock_trafilatura.extract.return_value = short_text

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.text = "<html><body>Short</body></html>"
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.pipeline_steps.httpx.get", return_value=mock_response):
            result = enrich_article_body("https://example.com/article")

        assert result == short_text


class TestNormalizeContentEnrichmentEnabled:
    """normalize_content calls enrichment when ARTICLE_ENRICHMENT_ENABLED=True."""

    @patch("app.services.pipeline_steps.enrich_article_body")
    def test_enrichment_called_when_enabled(self, mock_enrich):
        """When enrichment is enabled, enrich_article_body is called for items with URLs."""
        mock_enrich.return_value = "Enriched article body text."

        class FakeFeed:
            id = "feed-test"
            type = "rss"
            name = "Test Feed"

        raw_items = [
            {
                "title": "Article One",
                "url": "https://example.com/1",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "A short summary",
                "raw_text": "Original feed text",
            },
        ]

        with patch(
            "app.services.pipeline_steps.settings.ARTICLE_ENRICHMENT_ENABLED", True
        ):
            items, skipped = normalize_content("ws-1", FakeFeed(), raw_items)

        assert len(items) == 1
        mock_enrich.assert_called_once()
        # raw_text should be overridden with enriched content
        assert items[0].raw_text == "Enriched article body text."

    @patch("app.services.pipeline_steps.enrich_article_body")
    def test_raw_text_preserved_when_enrichment_returns_none(self, mock_enrich):
        """When enrichment returns None, original raw_text is preserved."""
        mock_enrich.return_value = None

        class FakeFeed:
            id = "feed-test"
            type = "rss"
            name = "Test Feed"

        raw_items = [
            {
                "title": "Article One",
                "url": "https://example.com/1",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "A short summary",
                "raw_text": "Original feed text",
            },
        ]

        with patch(
            "app.services.pipeline_steps.settings.ARTICLE_ENRICHMENT_ENABLED", True
        ):
            items, skipped = normalize_content("ws-1", FakeFeed(), raw_items)

        assert len(items) == 1
        mock_enrich.assert_called_once()
        # raw_text should remain as the original
        assert items[0].raw_text == "Original feed text"

    @patch("app.services.pipeline_steps.enrich_article_body")
    def test_enrichment_skipped_for_items_without_url(self, mock_enrich):
        """Items without a URL do not trigger enrichment."""
        mock_enrich.return_value = "Enriched text"

        class FakeFeed:
            id = "feed-test"
            type = "rss"
            name = "Test Feed"

        raw_items = [
            {
                "title": "Article No URL",
                "url": "",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "A short summary",
                "raw_text": "Original text",
            },
        ]

        with patch(
            "app.services.pipeline_steps.settings.ARTICLE_ENRICHMENT_ENABLED", True
        ):
            items, skipped = normalize_content("ws-1", FakeFeed(), raw_items)

        mock_enrich.assert_not_called()
        assert items[0].raw_text == "Original text"


class TestNormalizeContentEnrichmentDisabled:
    """normalize_content does not call enrichment when ARTICLE_ENRICHMENT_ENABLED=False."""

    @patch("app.services.pipeline_steps.enrich_article_body")
    def test_enrichment_not_called_when_disabled(self, mock_enrich):
        """When enrichment is disabled (default), enrich_article_body is never called."""
        mock_enrich.return_value = "Should not be used"

        class FakeFeed:
            id = "feed-test"
            type = "rss"
            name = "Test Feed"

        raw_items = [
            {
                "title": "Article One",
                "url": "https://example.com/1",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "A short summary",
                "raw_text": "Original feed text",
            },
        ]

        # Default is ARTICLE_ENRICHMENT_ENABLED=False, but explicitly patch for clarity
        with patch(
            "app.services.pipeline_steps.settings.ARTICLE_ENRICHMENT_ENABLED", False
        ):
            items, skipped = normalize_content("ws-1", FakeFeed(), raw_items)

        assert len(items) == 1
        mock_enrich.assert_not_called()
        # raw_text should remain as the original feed text
        assert items[0].raw_text == "Original feed text"


# ---------------------------------------------------------------------------
# Google News URL resolution tests
# ---------------------------------------------------------------------------


class TestResolveNewsUrl:
    """resolve_news_url resolves Google News redirect URLs."""

    GOOGLE_RSS_URL = (
        "https://news.google.com/rss/articles/CBMiigFBVV95cUxQYU1MaDRVZXpaeEdY"
        "YWJZOGw3MTQtTWVOSXh1UF9OS0drcXdhU0R5akVicnZRV0JUbUJlcXI1LVBhNDVXakdR"
        "QW5yN2hXT0xHODUtRkJhTDBkcXVTT0ZjLWRiNFh4d1k2MDRQZjJPa2NWSmstdkZlWnNL"
        "RXJQV3ZfZ0RxQWtibzhaYWc?oc=5"
    )
    CANONICAL_URL = "https://www.reuters.com/world/article-canonical-123/"

    def test_resolve_google_news_redirect_url(self):
        """Google News redirect URL is resolved to the canonical article URL."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.url = self.CANONICAL_URL
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.head.return_value = mock_response

        with patch(
            "app.services.pipeline_steps.httpx.Client", return_value=mock_client
        ):
            result = resolve_news_url(self.GOOGLE_RSS_URL)

        assert result == self.CANONICAL_URL

    def test_resolve_non_google_url_unchanged(self):
        """Non-Google URLs pass through unchanged (no HTTP call)."""
        with patch("app.services.pipeline_steps.httpx.Client") as mock_client_cls:
            result = resolve_news_url("https://www.reuters.com/world/some-article")

        assert result == "https://www.reuters.com/world/some-article"
        mock_client_cls.assert_not_called()

    def test_resolve_google_news_url_failure_falls_back(self):
        """On network error, falls back to the original Google News URL."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.head.side_effect = httpx.TimeoutException("timeout")

        with patch(
            "app.services.pipeline_steps.httpx.Client", return_value=mock_client
        ):
            result = resolve_news_url(self.GOOGLE_RSS_URL)

        assert result == self.GOOGLE_RSS_URL

    def test_resolve_google_news_403_falls_back(self):
        """On HTTP 403, falls back to the original Google News URL."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Forbidden",
            request=MagicMock(),
            response=MagicMock(status_code=403),
        )

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.head.return_value = mock_response

        with patch(
            "app.services.pipeline_steps.httpx.Client", return_value=mock_client
        ):
            result = resolve_news_url(self.GOOGLE_RSS_URL)

        assert result == self.GOOGLE_RSS_URL

    def test_resolve_empty_url(self):
        """Empty string returns empty string."""
        assert resolve_news_url("") == ""

    def test_resolve_none_like_empty(self):
        """None is handled gracefully (returns original value)."""
        # The function type hint says str, but we test defensive behaviour
        assert resolve_news_url(None) is None  # type: ignore[arg-type]

    def test_resolve_google_news_articles_path(self):
        """URLs with /articles/ (without /rss/) are also matched."""
        url = "https://news.google.com/articles/CBMiigFBVV95cUxQ?oc=5"
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.url = "https://example.com/canonical"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.head.return_value = mock_response

        with patch(
            "app.services.pipeline_steps.httpx.Client", return_value=mock_client
        ):
            result = resolve_news_url(url)

        assert result == "https://example.com/canonical"

    def test_resolve_google_news_stays_on_google_falls_back(self):
        """When the resolved URL is still a Google News URL, return original."""
        url = self.GOOGLE_RSS_URL
        # Simulate Google redirecting to locale-param variant (still Google)
        resolved_still_google = (
            "https://news.google.com/rss/articles/CBMiigFBVV95cUxQYU1MaDRVZXpaeEdY"
            "?hl=en-US&gl=US&ceid=US:en&oc=5"
        )
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.url = resolved_still_google
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.head.return_value = mock_response

        with patch(
            "app.services.pipeline_steps.httpx.Client", return_value=mock_client
        ):
            result = resolve_news_url(url)

        assert result == url


class TestPickBestUrl:
    """_pick_best_url selects the best URL from feedparser entries."""

    GOOGLE_RSS_URL = "https://news.google.com/rss/articles/CBMiigFBVV95cUxQ?oc=5"
    CANONICAL_URL = "https://www.reuters.com/world/article-123/"

    def test_prefers_alternate_link_when_primary_is_google_news(self):
        """When primary link is a Google News redirect and an alternate
        non-Google-News link exists, the alternate is preferred."""
        entry = {
            "link": self.GOOGLE_RSS_URL,
            "links": [
                {"rel": "alternate", "href": self.CANONICAL_URL, "type": "text/html"},
                {"rel": "self", "href": self.GOOGLE_RSS_URL},
            ],
        }
        result = _pick_best_url(entry)
        assert result == self.CANONICAL_URL

    def test_uses_primary_when_not_google_news(self):
        """When primary link is not a Google News URL, it is returned directly."""
        entry = {
            "link": "https://example.com/article",
            "links": [
                {"rel": "alternate", "href": "https://other.com/article"},
            ],
        }
        result = _pick_best_url(entry)
        assert result == "https://example.com/article"

    def test_falls_back_to_primary_when_no_alternate(self):
        """When all links are Google News URLs, falls back to primary."""
        entry = {
            "link": self.GOOGLE_RSS_URL,
            "links": [
                {"rel": "alternate", "href": self.GOOGLE_RSS_URL},
            ],
        }
        result = _pick_best_url(entry)
        assert result == self.GOOGLE_RSS_URL

    def test_falls_back_to_primary_when_links_missing(self):
        """When entry.links is missing, falls back to primary."""
        entry = {"link": self.GOOGLE_RSS_URL}
        result = _pick_best_url(entry)
        assert result == self.GOOGLE_RSS_URL

    def test_id_fallback(self):
        """When link is missing, falls back to id."""
        entry = {"id": "https://example.com/42"}
        result = _pick_best_url(entry)
        assert result == "https://example.com/42"

    def test_empty_entry(self):
        """Empty entry returns empty string."""
        entry = {}
        result = _pick_best_url(entry)
        assert result == ""


class TestExtractUrlResolvesGoogleNews:
    """Integration: _extract_url resolves Google News redirects."""

    GOOGLE_RSS_URL = "https://news.google.com/rss/articles/CBMiigFBVV95cUxQ?oc=5"
    CANONICAL_URL = "https://www.reuters.com/world/article-canonical/"

    @patch("app.services.pipeline_steps.httpx.Client")
    def test_extract_url_resolves_google_news_redirect(self, mock_client_cls):
        """_extract_url follows Google News redirect and normalises the result."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.url = self.CANONICAL_URL
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.head.return_value = mock_response
        mock_client_cls.return_value = mock_client

        entry = {"link": self.GOOGLE_RSS_URL}
        result = _extract_url(entry)

        assert result == "https://www.reuters.com/world/article-canonical"

    @patch("app.services.pipeline_steps.httpx.Client")
    def test_extract_url_falls_back_on_failure(self, mock_client_cls):
        """_extract_url falls back to normalised Google URL on resolution failure."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.head.side_effect = httpx.TimeoutException("timeout")
        mock_client_cls.return_value = mock_client

        entry = {"link": self.GOOGLE_RSS_URL}
        result = _extract_url(entry)

        # Should still return a normalised URL (the original Google URL)
        assert "news.google.com" in result

    @patch("app.services.pipeline_steps.httpx.Client")
    def test_extract_url_uses_alternate_link(self, mock_client_cls):
        """_extract_url uses alternate non-Google link and skips resolution."""
        entry = {
            "link": self.GOOGLE_RSS_URL,
            "links": [
                {"rel": "alternate", "href": self.CANONICAL_URL},
            ],
        }
        result = _extract_url(entry)

        # Should use the alternate link, no HTTP call needed
        assert result == "https://www.reuters.com/world/article-canonical"
        mock_client_cls.assert_not_called()

    def test_extract_url_non_google_unchanged(self):
        """Non-Google URLs are normalised but not resolved."""
        entry = {"link": "https://example.com/article?utm_source=tw"}
        result = _extract_url(entry)

        assert "utm_source" not in result
        assert result == "https://example.com/article"


# ---------------------------------------------------------------------------
# Publisher info extraction tests
# ---------------------------------------------------------------------------


class TestFetchFeedPublisherExtraction:
    """fetch_feed extracts per-entry publisher info from entry.source."""

    @patch("app.services.pipeline_steps.httpx.get")
    def test_extracts_publisher_name_from_entry_source(self, mock_get):
        """entry.source.title is used as publisher_name and effective source_name."""
        mock_response = MagicMock()
        mock_response.text = """
        <rss version="2.0">
          <channel>
            <title>Google News</title>
            <item>
              <title>Test Article</title>
              <link>https://news.google.com/rss/articles/test123</link>
              <source url="https://ruhrkanal.news">ruhrkanal.news</source>
              <pubDate>Wed, 20 Mar 2024 08:00:00 +0000</pubDate>
            </item>
          </channel>
        </rss>
        """
        mock_get.return_value = mock_response

        class FakeFeed:
            id = "feed-test"
            url = "https://news.google.com/rss?hl=en"
            name = "Test Feed"
            type = "rss"

        result = fetch_feed(FakeFeed())
        assert result.success is True
        assert len(result.entries) == 1

        entry = result.entries[0]
        assert entry["publisher_name"] == "ruhrkanal.news"
        assert entry["publisher_domain"] == "ruhrkanal.news"
        assert entry["source_name"] == "ruhrkanal.news"  # publisher takes priority

    @patch("app.services.pipeline_steps.httpx.get")
    def test_extracts_publisher_domain_from_href(self, mock_get):
        """entry.source.href provides the publisher domain."""
        mock_response = MagicMock()
        mock_response.text = """
        <rss version="2.0">
          <channel>
            <title>Google News</title>
            <item>
              <title>Toy Industry News</title>
              <link>https://news.google.com/rss/articles/toy123</link>
              <source>
                <title>The Toy Book</title>
                <link>https://toybook.com</link>
              </source>
              <pubDate>Wed, 20 Mar 2024 08:00:00 +0000</pubDate>
            </item>
          </channel>
        </rss>
        """
        mock_get.return_value = mock_response

        class FakeFeed:
            id = "feed-test"
            url = "https://news.google.com/rss?hl=en"
            name = "Test Feed"
            type = "rss"

        result = fetch_feed(FakeFeed())
        assert result.success is True
        entry = result.entries[0]
        assert entry["publisher_name"] == "The Toy Book"
        assert entry["publisher_domain"] == "toybook.com"
        assert entry["source_name"] == "The Toy Book"

    @patch("app.services.pipeline_steps.httpx.get")
    def test_fallback_when_entry_source_missing(self, mock_get):
        """When entry.source is missing, falls back to feed-level title."""
        mock_response = MagicMock()
        mock_response.text = """
        <rss version="2.0">
          <channel>
            <title>Some RSS Feed</title>
            <item>
              <title>Test Article</title>
              <link>https://example.com/article1</link>
              <pubDate>Wed, 20 Mar 2024 08:00:00 +0000</pubDate>
            </item>
          </channel>
        </rss>
        """
        mock_get.return_value = mock_response

        class FakeFeed:
            id = "feed-test"
            url = "https://example.com/feed.xml"
            name = "Test Feed"
            type = "rss"

        result = fetch_feed(FakeFeed())
        assert result.success is True
        entry = result.entries[0]
        assert entry["publisher_name"] is None
        assert entry["publisher_domain"] is None
        assert entry["source_name"] == "Some RSS Feed"  # feed-level title

    @patch("app.services.pipeline_steps.httpx.get")
    def test_publisher_name_none_when_source_has_no_title(self, mock_get):
        """When entry.source exists but has no title, publisher_name is None."""
        mock_response = MagicMock()
        mock_response.text = """
        <rss version="2.0">
          <channel>
            <title>Google News</title>
            <item>
              <title>Test Article</title>
              <link>https://example.com/article1</link>
              <source>
                <link>https://somedomain.com</link>
              </source>
              <pubDate>Wed, 20 Mar 2024 08:00:00 +0000</pubDate>
            </item>
          </channel>
        </rss>
        """
        mock_get.return_value = mock_response

        class FakeFeed:
            id = "feed-test"
            url = "https://news.google.com/rss"
            name = "Test Feed"
            type = "rss"

        result = fetch_feed(FakeFeed())
        assert result.success is True
        entry = result.entries[0]
        assert entry["publisher_name"] is None
        assert entry["publisher_domain"] == "somedomain.com"
        # Falls back to feed-level title when publisher_name is None
        assert entry["source_name"] == "Google News"


class TestNormalizeContentPublisherFields:
    """normalize_content passes publisher_name and publisher_domain to ContentItem."""

    def test_publisher_fields_stored_on_content_item(self):
        """publisher_name and publisher_domain are stored on ContentItem."""

        class FakeFeed:
            id = "feed-test"
            type = "rss"
            name = "Test Feed"

        raw_items = [
            {
                "title": "Article One",
                "url": "https://example.com/1",
                "source_name": "Publisher Name",
                "publisher_name": "Publisher Name",
                "publisher_domain": "publisher.com",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "A short summary",
                "raw_text": "Full content here",
            },
        ]

        items, skipped = normalize_content("ws-1", FakeFeed(), raw_items)
        assert len(items) == 1
        assert items[0].publisher_name == "Publisher Name"
        assert items[0].publisher_domain == "publisher.com"

    def test_publisher_fields_none_when_missing(self):
        """Missing publisher fields result in None on ContentItem."""

        class FakeFeed:
            id = "feed-test"
            type = "rss"
            name = "Test Feed"

        raw_items = [
            {
                "title": "Article One",
                "url": "https://example.com/1",
                "source_name": "Feed Title",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "A short summary",
                "raw_text": "Full content here",
            },
        ]

        items, skipped = normalize_content("ws-1", FakeFeed(), raw_items)
        assert len(items) == 1
        assert items[0].publisher_name is None
        assert items[0].publisher_domain is None
