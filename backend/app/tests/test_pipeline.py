"""Tests for pipeline helper functions."""

from datetime import datetime, timezone

from app.tasks.pipeline import (
    fetch_feed,
    generate_report_stub,
    normalize_content,
    parse_rfc2822,
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
                "content": "Full content here",
            },
        ]

        items = normalize_content("ws-1", FakeFeed(), raw_items)
        assert len(items) == 1

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
                "content": "",
            },
        ]

        items = normalize_content("ws-1", FakeFeed(), raw_items)
        assert items[0].content_type == "blog"

    def test_normalize_content_empty(self):
        """Empty raw items list produces empty ContentItem list."""

        class FakeFeed:
            id = "feed-empty"
            type = "rss"
            name = "Empty"

        items = normalize_content("ws-1", FakeFeed(), [])
        assert items == []

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
                "content": "",
            },
        ]

        items = normalize_content("ws-1", FakeFeed(), raw_items)
        assert len(items[0].title) <= 1000
        assert len(items[0].url) <= 2048
        assert len(items[0].summary_snippet) <= 500


class TestGenerateReportStub:
    """generate_report_stub creates a Report from content items."""

    def test_generate_report_stub_with_items(self):
        """Report is generated with included items as highlights."""

        # Build lightweight fakes
        class FakeWorkspace:
            id = "ws-1"
            customer = "TestCo"

        class FakeRun:
            id = "run-1"

        class FakeItem:
            title = "Important Article"
            source_name = "TechCrunch"
            url = "https://techcrunch.com/article"
            summary_snippet = "A very important summary"
            status = "included"

        report = generate_report_stub(FakeWorkspace(), [FakeItem()], FakeRun())
        assert "TestCo" in report.title
        assert "Daily News Digest" in report.title
        assert "Important Article" in report.markdown_body
        assert report.status == "published"
        assert report.workspace_id == "ws-1"
        assert report.run_id == "run-1"

    def test_generate_report_stub_empty_items(self):
        """Report with zero items still has header and summary."""

        class FakeWorkspace:
            id = "ws-1"
            customer = "EmptyCo"

        class FakeRun:
            id = "run-1"

        report = generate_report_stub(FakeWorkspace(), [], FakeRun())
        assert "0 articles" in report.markdown_body
        assert report.status == "published"

    def test_generate_report_stub_falls_back_to_first_five(self):
        """When no items are 'included', first five are used."""

        class FakeWorkspace:
            id = "ws-1"
            customer = "FallbackCo"

        class FakeRun:
            id = "run-1"

        items = []
        for i in range(8):
            item = type(
                "Item",
                (),
                {
                    "title": f"Article {i}",
                    "source_name": "Source",
                    "url": f"https://example.com/{i}",
                    "summary_snippet": f"Summary {i}",
                    "status": "pending",
                },
            )()
            items.append(item)

        report = generate_report_stub(FakeWorkspace(), items, FakeRun())
        # Should include first 5 pending items as fallback
        assert "Article 0" in report.markdown_body
        assert "Article 4" in report.markdown_body
        assert "Article 5" not in report.markdown_body
