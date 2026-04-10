"""Tests for idempotent ingestion behaviour of normalize_content."""

from datetime import datetime, timezone

import pytest

from app.models.content import ContentItem
from app.services.pipeline_steps import compute_source_entry_id, normalize_content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeFeed:
    """Lightweight stand-in for FeedSource — no DB required."""

    def __init__(
        self,
        feed_id: str = "feed-test",
        feed_type: str = "rss",
        name: str = "Test Feed",
    ):
        self.id = feed_id
        self.type = feed_type
        self.name = name


def _make_raw_items(count: int, base_url: str = "https://example.com") -> list[dict]:
    """Create *count* distinct raw feed-item dicts."""
    items: list[dict] = []
    for i in range(count):
        items.append(
            {
                "title": f"Article {i + 1}",
                "url": f"{base_url}/{i + 1}",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 20 + i, tzinfo=timezone.utc),
                "author": f"Author {i + 1}",
                "summary": f"Summary for article {i + 1}",
                "raw_text": f"Full content for article {i + 1}",
            }
        )
    return items


# ---------------------------------------------------------------------------
# 1. Repeated ingestion
# ---------------------------------------------------------------------------


class TestRepeatedIngestion:
    """Calling normalize_content twice with the same data is idempotent."""

    def test_first_call_creates_second_call_skips(self, db_session):
        """First call creates N items; second call creates 0, skips N."""
        feed = FakeFeed()
        raw_items = _make_raw_items(3)

        # --- First ingestion ---
        items_1, skipped_1 = normalize_content("ws-1", feed, raw_items, db=db_session)
        assert len(items_1) == 3
        assert skipped_1 == 0

        # Persist the first batch into the DB so the second call can detect them.
        for item in items_1:
            db_session.add(item)
        db_session.commit()

        # --- Second ingestion (same workspace, same entries) ---
        items_2, skipped_2 = normalize_content("ws-1", feed, raw_items, db=db_session)
        assert len(items_2) == 0
        assert skipped_2 == 3

        # Total rows in DB should be exactly 3, not 6.
        total = db_session.query(ContentItem).filter_by(workspace_id="ws-1").count()
        assert total == 3

    def test_total_count_remains_n_after_double_ingest(self, db_session):
        """Total ContentItem count is N after two identical ingestion passes."""
        feed = FakeFeed()
        raw_items = _make_raw_items(5)

        # First pass
        items_1, skipped_1 = normalize_content("ws-1", feed, raw_items, db=db_session)
        for item in items_1:
            db_session.add(item)
        db_session.commit()

        # Second pass
        items_2, skipped_2 = normalize_content("ws-1", feed, raw_items, db=db_session)
        for item in items_2:
            db_session.add(item)
        db_session.commit()

        assert db_session.query(ContentItem).filter_by(workspace_id="ws-1").count() == 5


# ---------------------------------------------------------------------------
# 2. Mixed new + already-known entries
# ---------------------------------------------------------------------------


class TestMixedNewAndKnownEntries:
    """Second ingestion with a mix of new and previously-seen entries."""

    def test_second_call_creates_only_new_entries(self, db_session):
        """First call imports A, B, C. Second call has B, C, D → only D created."""
        feed = FakeFeed()

        # Entries A, B, C
        raw_first = [
            {
                "title": "Entry A",
                "url": "https://example.com/a",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "Summary A",
                "raw_text": "Content A",
            },
            {
                "title": "Entry B",
                "url": "https://example.com/b",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 21, tzinfo=timezone.utc),
                "author": "Bob",
                "summary": "Summary B",
                "raw_text": "Content B",
            },
            {
                "title": "Entry C",
                "url": "https://example.com/c",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 22, tzinfo=timezone.utc),
                "author": "Carol",
                "summary": "Summary C",
                "raw_text": "Content C",
            },
        ]

        # --- First ingestion ---
        items_1, skipped_1 = normalize_content("ws-1", feed, raw_first, db=db_session)
        assert len(items_1) == 3
        assert skipped_1 == 0
        for item in items_1:
            db_session.add(item)
        db_session.commit()

        # Entries B, C, D (B and C already exist, D is new)
        raw_second = [
            {
                "title": "Entry B",
                "url": "https://example.com/b",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 21, tzinfo=timezone.utc),
                "author": "Bob",
                "summary": "Summary B",
                "raw_text": "Content B",
            },
            {
                "title": "Entry C",
                "url": "https://example.com/c",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 22, tzinfo=timezone.utc),
                "author": "Carol",
                "summary": "Summary C",
                "raw_text": "Content C",
            },
            {
                "title": "Entry D",
                "url": "https://example.com/d",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 23, tzinfo=timezone.utc),
                "author": "Dave",
                "summary": "Summary D",
                "raw_text": "Content D",
            },
        ]

        # --- Second ingestion ---
        items_2, skipped_2 = normalize_content("ws-1", feed, raw_second, db=db_session)
        assert len(items_2) == 1
        assert skipped_2 == 2
        assert items_2[0].title == "Entry D"

        # Persist the new entry.
        for item in items_2:
            db_session.add(item)
        db_session.commit()

        # Total rows should be 4 (A + B + C + D).
        total = db_session.query(ContentItem).filter_by(workspace_id="ws-1").count()
        assert total == 4


# ---------------------------------------------------------------------------
# 3. source_entry_id population
# ---------------------------------------------------------------------------


class TestSourceEntryIdPopulation:
    """Every created ContentItem must have source_entry_id populated."""

    def test_url_based_source_entry_id(self, db_session):
        """source_entry_id is the normalized URL when URL is present."""
        feed = FakeFeed()
        raw_items = [
            {
                "title": "Article",
                "url": "https://example.com/article?utm_source=tw",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "Summary",
                "raw_text": "Content",
            },
        ]

        items, _ = normalize_content("ws-1", feed, raw_items)
        assert len(items) == 1
        entry_id = items[0].source_entry_id
        assert entry_id is not None
        # Tracking params should have been stripped
        assert "utm_source" not in entry_id
        assert "example.com/article" in entry_id

    def test_all_items_have_source_entry_id_after_db_persist(self, db_session):
        """After persisting, every DB row has a non-null source_entry_id."""
        feed = FakeFeed()
        raw_items = _make_raw_items(4)

        items, _ = normalize_content("ws-1", feed, raw_items, db=db_session)
        for item in items:
            db_session.add(item)
        db_session.commit()

        rows = db_session.query(ContentItem).filter_by(workspace_id="ws-1").all()
        assert len(rows) == 4
        for row in rows:
            assert row.source_entry_id is not None, (
                f"Row {row.id} has null source_entry_id"
            )

    def test_source_entry_id_matches_compute_helper(self):
        """The source_entry_id stored on the item matches compute_source_entry_id()."""
        feed = FakeFeed()
        raw = {
            "title": "Match Test",
            "url": "https://example.com/match-test",
            "source_name": "Example",
            "published_at": datetime(2024, 6, 1, tzinfo=timezone.utc),
            "author": "Writer",
            "summary": "Sum",
            "raw_text": "Text",
        }

        items, _ = normalize_content("ws-1", feed, [raw])
        assert items[0].source_entry_id == compute_source_entry_id(raw)


# ---------------------------------------------------------------------------
# 4. Fallback identity (no URL)
# ---------------------------------------------------------------------------


class TestFallbackIdentity:
    """Entries without a URL use a SHA-256 composite hash as source_entry_id."""

    def test_no_url_uses_composite_hash(self):
        """When URL is empty, source_entry_id is a SHA-256 hex digest."""
        raw = {
            "title": "No-URL Article",
            "url": "",
            "source_name": "TestSource",
            "published_at": datetime(2024, 4, 10, tzinfo=timezone.utc),
        }
        entry_id = compute_source_entry_id(raw)
        assert entry_id is not None
        # SHA-256 hex digests are 64 characters long
        assert len(entry_id) == 64
        # Should only contain hex characters
        assert all(c in "0123456789abcdef" for c in entry_id)

    def test_no_url_idempotency_with_db(self, db_session):
        """Repeated ingestion of URL-less entries is still idempotent."""
        feed = FakeFeed()
        raw_items = [
            {
                "title": "No-URL Entry A",
                "url": "",
                "source_name": "SourceX",
                "published_at": datetime(2024, 4, 10, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "Summary A",
                "raw_text": "Content A",
            },
            {
                "title": "No-URL Entry B",
                "url": "",
                "source_name": "SourceX",
                "published_at": datetime(2024, 4, 11, tzinfo=timezone.utc),
                "author": "Bob",
                "summary": "Summary B",
                "raw_text": "Content B",
            },
        ]

        # --- First pass ---
        items_1, skipped_1 = normalize_content("ws-1", feed, raw_items, db=db_session)
        assert len(items_1) == 2
        assert skipped_1 == 0
        for item in items_1:
            db_session.add(item)
        db_session.commit()

        # --- Second pass (identical) ---
        items_2, skipped_2 = normalize_content("ws-1", feed, raw_items, db=db_session)
        assert len(items_2) == 0
        assert skipped_2 == 2

    def test_no_url_different_content_not_skipped(self, db_session):
        """Different URL-less entries are NOT treated as duplicates."""
        feed = FakeFeed()
        raw_first = [
            {
                "title": "First Title",
                "url": "",
                "source_name": "SourceX",
                "published_at": datetime(2024, 4, 10, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "Summary",
                "raw_text": "Content",
            },
        ]
        raw_second = [
            {
                "title": "Different Title",
                "url": "",
                "source_name": "SourceX",
                "published_at": datetime(2024, 4, 10, tzinfo=timezone.utc),
                "author": "Bob",
                "summary": "Summary",
                "raw_text": "Content",
            },
        ]

        # First pass
        items_1, skipped_1 = normalize_content("ws-1", feed, raw_first, db=db_session)
        assert len(items_1) == 1
        for item in items_1:
            db_session.add(item)
        db_session.commit()

        # Second pass — different title, should NOT be skipped
        items_2, skipped_2 = normalize_content("ws-1", feed, raw_second, db=db_session)
        assert len(items_2) == 1
        assert skipped_2 == 0

    def test_composite_hash_changes_when_fields_differ(self):
        """Changing any field in the composite changes the hash."""
        raw_base = {
            "title": "Title",
            "url": "",
            "source_name": "Source",
            "published_at": datetime(2024, 4, 10, tzinfo=timezone.utc),
        }
        raw_different_title = {**raw_base, "title": "Other Title"}
        raw_different_source = {**raw_base, "source_name": "Other Source"}
        raw_different_date = {
            **raw_base,
            "published_at": datetime(2024, 4, 11, tzinfo=timezone.utc),
        }

        base_id = compute_source_entry_id(raw_base)
        assert compute_source_entry_id(raw_different_title) != base_id
        assert compute_source_entry_id(raw_different_source) != base_id
        assert compute_source_entry_id(raw_different_date) != base_id


# ---------------------------------------------------------------------------
# 5. Cross-workspace isolation
# ---------------------------------------------------------------------------


class TestCrossWorkspaceIsolation:
    """Same feed entry imported for different workspaces is NOT skipped."""

    def test_same_entry_different_workspaces(self, db_session):
        """Entry imported for workspace A does NOT get skipped for workspace B."""
        feed = FakeFeed()
        raw_items = [
            {
                "title": "Shared Article",
                "url": "https://example.com/shared",
                "source_name": "Example",
                "published_at": datetime(2024, 5, 1, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "Shared summary",
                "raw_text": "Shared content",
            },
        ]

        # --- Import for workspace A ---
        items_a, skipped_a = normalize_content("ws-a", feed, raw_items, db=db_session)
        assert len(items_a) == 1
        assert skipped_a == 0
        for item in items_a:
            db_session.add(item)
        db_session.commit()

        # --- Import same entry for workspace B ---
        items_b, skipped_b = normalize_content("ws-b", feed, raw_items, db=db_session)
        assert len(items_b) == 1
        assert skipped_b == 0  # Not skipped — different workspace

        for item in items_b:
            db_session.add(item)
        db_session.commit()

        # Both workspaces should each have exactly 1 row.
        assert db_session.query(ContentItem).filter_by(workspace_id="ws-a").count() == 1
        assert db_session.query(ContentItem).filter_by(workspace_id="ws-b").count() == 1

    def test_partial_overlap_across_workspaces(self, db_session):
        """Workspace A has entries X, Y. Workspace B imports Y, Z → only Y skipped in B."""
        feed = FakeFeed()

        entry_x = {
            "title": "Entry X",
            "url": "https://example.com/x",
            "source_name": "Example",
            "published_at": datetime(2024, 5, 1, tzinfo=timezone.utc),
            "author": "Alice",
            "summary": "Sum X",
            "raw_text": "Text X",
        }
        entry_y = {
            "title": "Entry Y",
            "url": "https://example.com/y",
            "source_name": "Example",
            "published_at": datetime(2024, 5, 2, tzinfo=timezone.utc),
            "author": "Bob",
            "summary": "Sum Y",
            "raw_text": "Text Y",
        }
        entry_z = {
            "title": "Entry Z",
            "url": "https://example.com/z",
            "source_name": "Example",
            "published_at": datetime(2024, 5, 3, tzinfo=timezone.utc),
            "author": "Carol",
            "summary": "Sum Z",
            "raw_text": "Text Z",
        }

        # Workspace A: import X, Y
        items_a, skipped_a = normalize_content(
            "ws-a", feed, [entry_x, entry_y], db=db_session
        )
        assert len(items_a) == 2
        assert skipped_a == 0
        for item in items_a:
            db_session.add(item)
        db_session.commit()

        # Workspace B: import Y, Z — Y was already imported for A but NOT for B
        items_b, skipped_b = normalize_content(
            "ws-b", feed, [entry_y, entry_z], db=db_session
        )
        assert len(items_b) == 2
        assert skipped_b == 0  # Neither skipped — different workspace

        for item in items_b:
            db_session.add(item)
        db_session.commit()

        assert db_session.query(ContentItem).filter_by(workspace_id="ws-a").count() == 2
        assert db_session.query(ContentItem).filter_by(workspace_id="ws-b").count() == 2


# ---------------------------------------------------------------------------
# 6. Within-batch deduplication
# ---------------------------------------------------------------------------


class TestWithinBatchDedup:
    """Duplicate entries *within the same batch* are collapsed."""

    def test_identical_urls_produce_one_item(self, db_session):
        """A batch with 2 identical URLs yields 1 ContentItem; skipped_count=1."""
        feed = FakeFeed()
        raw_items = [
            {
                "title": "Article",
                "url": "https://example.com/article",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "Summary",
                "raw_text": "Content",
            },
            {
                "title": "Article (duplicate)",
                "url": "https://example.com/article",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "Summary",
                "raw_text": "Content",
            },
        ]

        items, skipped = normalize_content("ws-1", feed, raw_items, db=db_session)
        assert len(items) == 1
        assert skipped == 1
        assert items[0].url == "https://example.com/article"

    def test_tracking_params_treated_as_same_url(self, db_session):
        """URL and URL+fbclid normalize to the same entry; 1 item, skipped=1."""
        feed = FakeFeed()
        raw_items = [
            {
                "title": "Article",
                "url": "https://example.com/article",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "Summary",
                "raw_text": "Content",
            },
            {
                "title": "Article (fbclid)",
                "url": "https://example.com/article?fbclid=123",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "Summary",
                "raw_text": "Content",
            },
        ]

        items, skipped = normalize_content("ws-1", feed, raw_items, db=db_session)
        assert len(items) == 1
        assert skipped == 1
        # The stored URL should be the first one seen (without fbclid)
        assert "fbclid" not in items[0].url

    def test_mixed_duplicates_and_new(self, db_session):
        """Batch A, B, A, C → 3 items (A, B, C) with skipped_count=1."""
        feed = FakeFeed()
        raw_items = [
            {
                "title": "Entry A",
                "url": "https://example.com/a",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "Sum A",
                "raw_text": "Text A",
            },
            {
                "title": "Entry B",
                "url": "https://example.com/b",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 21, tzinfo=timezone.utc),
                "author": "Bob",
                "summary": "Sum B",
                "raw_text": "Text B",
            },
            {
                "title": "Entry A (again)",
                "url": "https://example.com/a",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "Sum A",
                "raw_text": "Text A",
            },
            {
                "title": "Entry C",
                "url": "https://example.com/c",
                "source_name": "Example",
                "published_at": datetime(2024, 3, 22, tzinfo=timezone.utc),
                "author": "Carol",
                "summary": "Sum C",
                "raw_text": "Text C",
            },
        ]

        items, skipped = normalize_content("ws-1", feed, raw_items, db=db_session)
        assert len(items) == 3
        assert skipped == 1
        urls = {item.url for item in items}
        assert urls == {
            "https://example.com/a",
            "https://example.com/b",
            "https://example.com/c",
        }

    def test_within_batch_and_db_dedup_combined(self, db_session):
        """First batch A, B, C. Second batch A, D → 4 total, 1 skipped in second."""
        feed = FakeFeed()

        entry_a = {
            "title": "Entry A",
            "url": "https://example.com/a",
            "source_name": "Example",
            "published_at": datetime(2024, 3, 20, tzinfo=timezone.utc),
            "author": "Alice",
            "summary": "Sum A",
            "raw_text": "Text A",
        }
        entry_b = {
            "title": "Entry B",
            "url": "https://example.com/b",
            "source_name": "Example",
            "published_at": datetime(2024, 3, 21, tzinfo=timezone.utc),
            "author": "Bob",
            "summary": "Sum B",
            "raw_text": "Text B",
        }
        entry_c = {
            "title": "Entry C",
            "url": "https://example.com/c",
            "source_name": "Example",
            "published_at": datetime(2024, 3, 22, tzinfo=timezone.utc),
            "author": "Carol",
            "summary": "Sum C",
            "raw_text": "Text C",
        }
        entry_d = {
            "title": "Entry D",
            "url": "https://example.com/d",
            "source_name": "Example",
            "published_at": datetime(2024, 3, 23, tzinfo=timezone.utc),
            "author": "Dave",
            "summary": "Sum D",
            "raw_text": "Text D",
        }

        # --- First batch: A, B, C ---
        items_1, skipped_1 = normalize_content(
            "ws-1", feed, [entry_a, entry_b, entry_c], db=db_session
        )
        assert len(items_1) == 3
        assert skipped_1 == 0
        for item in items_1:
            db_session.add(item)
        db_session.commit()

        # --- Second batch: A (already in DB), D (new) ---
        items_2, skipped_2 = normalize_content(
            "ws-1", feed, [entry_a, entry_d], db=db_session
        )
        assert len(items_2) == 1
        assert skipped_2 == 1
        assert items_2[0].title == "Entry D"

        for item in items_2:
            db_session.add(item)
        db_session.commit()

        # Total should be 4 (A + B + C + D).
        total = db_session.query(ContentItem).filter_by(workspace_id="ws-1").count()
        assert total == 4


# ---------------------------------------------------------------------------
# 7. Long URL / source_entry_id persistence
# ---------------------------------------------------------------------------


class TestSourceEntryIdLongUrl:
    """Long URLs (300+ chars) persist correctly and dedup works."""

    @staticmethod
    def _build_long_url(min_length: int = 300) -> str:
        """Construct a deterministic URL exceeding *min_length* characters."""
        base = "https://example.com/articles/"
        # Pad with path segments to reach the desired length
        path = "a" * (min_length - len(base) - 30)
        query = "?page=1&category=tech&sort=date"
        url = base + path + query
        assert len(url) >= min_length
        return url

    @staticmethod
    def _build_very_long_url(min_length: int = 500) -> str:
        """Construct a URL exceeding *min_length* with many query params."""
        base = "https://example.com/very/deeply/nested/path/"
        path = "b" * (min_length - len(base) - 200)
        # Non-tracking query params so they survive normalization
        params = "&".join(f"param{k}=value{k}" for k in range(1, 16))
        url = base + path + "?" + params
        assert len(url) >= min_length
        return url

    def test_long_url_persists_correctly(self, db_session):
        """A URL with 300+ chars is stored without truncation."""
        long_url = self._build_long_url(300)
        expected_entry_id = compute_source_entry_id({"url": long_url})

        feed = FakeFeed()
        raw_items = [
            {
                "title": "Long URL Article",
                "url": long_url,
                "source_name": "Example",
                "published_at": datetime(2024, 7, 1, tzinfo=timezone.utc),
                "author": "Alice",
                "summary": "Summary",
                "raw_text": "Content",
            },
        ]

        items, skipped = normalize_content("ws-1", feed, raw_items, db=db_session)
        assert len(items) == 1
        assert skipped == 0

        item = items[0]
        # source_entry_id must be set to the full normalized URL
        assert item.source_entry_id == expected_entry_id
        # Must not be truncated — should be the same length as the computed ID
        assert len(item.source_entry_id) == len(expected_entry_id)
        assert len(item.source_entry_id) > 255

        # Persist and verify from DB
        db_session.add(item)
        db_session.commit()

        row = db_session.query(ContentItem).filter_by(workspace_id="ws-1").one()
        assert row.source_entry_id == expected_entry_id
        assert row.source_entry_id is not None
        assert len(row.source_entry_id) == len(expected_entry_id)

    def test_very_long_url_with_query_params(self, db_session):
        """A URL with 500+ chars and many query params persists and dedup works."""
        very_long_url = self._build_very_long_url(500)
        expected_entry_id = compute_source_entry_id({"url": very_long_url})

        feed = FakeFeed()
        raw_items = [
            {
                "title": "Very Long URL Article",
                "url": very_long_url,
                "source_name": "Example",
                "published_at": datetime(2024, 7, 2, tzinfo=timezone.utc),
                "author": "Bob",
                "summary": "Summary",
                "raw_text": "Content",
            },
        ]

        # --- First ingestion ---
        items_1, skipped_1 = normalize_content("ws-1", feed, raw_items, db=db_session)
        assert len(items_1) == 1
        assert skipped_1 == 0
        assert items_1[0].source_entry_id == expected_entry_id

        for item in items_1:
            db_session.add(item)
        db_session.commit()

        # --- Second ingestion of the same long URL ---
        items_2, skipped_2 = normalize_content("ws-1", feed, raw_items, db=db_session)
        assert len(items_2) == 0
        assert skipped_2 == 1

        # Total rows should still be exactly 1
        total = db_session.query(ContentItem).filter_by(workspace_id="ws-1").count()
        assert total == 1

    def test_long_url_dedup_across_runs(self, db_session):
        """Ingesting the same long URL in a second run produces 0 new items."""
        long_url = self._build_long_url(300)
        expected_entry_id = compute_source_entry_id({"url": long_url})

        feed = FakeFeed()
        raw_items = [
            {
                "title": "Dedup Test Article",
                "url": long_url,
                "source_name": "Example",
                "published_at": datetime(2024, 7, 3, tzinfo=timezone.utc),
                "author": "Carol",
                "summary": "Summary",
                "raw_text": "Content",
            },
        ]

        # --- Batch 1 ---
        items_1, skipped_1 = normalize_content("ws-1", feed, raw_items, db=db_session)
        assert len(items_1) == 1
        assert skipped_1 == 0
        assert items_1[0].source_entry_id == expected_entry_id

        for item in items_1:
            db_session.add(item)
        db_session.commit()

        # --- Batch 2 (identical) ---
        items_2, skipped_2 = normalize_content("ws-1", feed, raw_items, db=db_session)
        assert len(items_2) == 0
        assert skipped_2 == 1

        # Verify the DB row still has the full source_entry_id
        total = db_session.query(ContentItem).filter_by(workspace_id="ws-1").count()
        assert total == 1
        row = db_session.query(ContentItem).filter_by(workspace_id="ws-1").one()
        assert row.source_entry_id == expected_entry_id
