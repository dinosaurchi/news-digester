"""Tests for dedup.py pure utility functions."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.dedup import (
    compute_similarity,
    extract_domain,
    normalize_title,
    normalize_url,
    time_proximity,
    title_fingerprint,
    token_overlap_similarity,
    trigram_similarity,
)


# ---------------------------------------------------------------------------
# normalize_url
# ---------------------------------------------------------------------------


class TestNormalizeUrl:
    """normalize_url produces a canonical URL for deduplication."""

    def test_strips_utm_tracking_params(self):
        """utm_source, utm_medium etc. are removed."""
        result = normalize_url(
            "https://example.com/article?utm_source=foo&utm_medium=bar"
        )
        assert result == "https://example.com/article"

    def test_strips_fbclid_gclid(self):
        """Facebook / Google click-IDs are stripped."""
        result = normalize_url("https://example.com/news?fbclid=abc123")
        assert result == "https://example.com/news"

        result = normalize_url("https://example.com/news?gclid=xyz789")
        assert result == "https://example.com/news"

    def test_removes_fragments(self):
        """The #section fragment is dropped."""
        result = normalize_url("https://example.com/article#section")
        assert result == "https://example.com/article"

    def test_lowercases_hostname(self):
        """Scheme and hostname casing is normalised to lowercase."""
        result = normalize_url("HTTP://Example.COM/Path")
        assert result == "http://example.com/Path"

    def test_removes_trailing_slashes(self):
        """Trailing slash on the path is stripped."""
        result = normalize_url("https://example.com/article/")
        assert result == "https://example.com/article"

    def test_removes_trailing_slash_on_root(self):
        """Root path trailing slash is also removed."""
        result = normalize_url("https://example.com/")
        assert result == "https://example.com"

    def test_sorts_query_params(self):
        """Remaining query parameters are sorted alphabetically."""
        result = normalize_url("https://example.com/page?z=1&a=2")
        assert result == "https://example.com/page?a=2&z=1"

    def test_none_returns_empty_string(self):
        assert normalize_url(None) == ""

    def test_empty_string_returns_empty_string(self):
        assert normalize_url("") == ""

    def test_preserves_non_tracking_params(self):
        """Query params that are not in the tracking set are kept."""
        result = normalize_url("https://example.com/page?id=42&lang=en")
        assert result == "https://example.com/page?id=42&lang=en"


# ---------------------------------------------------------------------------
# normalize_title
# ---------------------------------------------------------------------------


class TestNormalizeTitle:
    """normalize_title lowercases, strips boundary punctuation, collapses spaces."""

    def test_lowercases(self):
        assert normalize_title("Big News") == "big news"

    def test_strips_boundary_punctuation(self):
        """Punctuation at the start/end of the title is stripped."""
        assert normalize_title("| Breaking News |") == "breaking news"

    def test_strips_dashes(self):
        """Dashes at the boundaries are stripped."""
        assert normalize_title("-Breaking News-") == "breaking news"

    def test_collapses_whitespace(self):
        """Runs of whitespace are collapsed to a single space."""
        assert normalize_title("Big   News") == "big news"

    def test_none_returns_empty_string(self):
        assert normalize_title(None) == ""

    def test_empty_string_returns_empty_string(self):
        assert normalize_title("") == ""

    def test_middle_pipe_is_preserved(self):
        """A pipe in the middle of the title is not stripped."""
        assert normalize_title("News | Tech") == "news | tech"


# ---------------------------------------------------------------------------
# title_fingerprint
# ---------------------------------------------------------------------------


class TestTitleFingerprint:
    """title_fingerprint returns a stable SHA-256 hex digest."""

    def test_same_title_same_hash(self):
        assert title_fingerprint("Hello World") == title_fingerprint("Hello World")

    def test_different_titles_different_hashes(self):
        assert title_fingerprint("Hello World") != title_fingerprint("Goodbye World")

    def test_case_and_spacing_normalised(self):
        """Titles differing only in case / whitespace produce the same hash."""
        assert title_fingerprint("Big NEWS") == title_fingerprint("big news")
        assert title_fingerprint("Big   News") == title_fingerprint("big news")

    def test_none_returns_hash_of_empty_string(self):
        assert title_fingerprint(None) == title_fingerprint("")

    def test_boundary_punctuation_normalised(self):
        """Titles differing only in boundary punctuation produce the same hash."""
        assert title_fingerprint("-Big News-") == title_fingerprint("big news")


# ---------------------------------------------------------------------------
# extract_domain
# ---------------------------------------------------------------------------


class TestExtractDomain:
    """extract_domain returns the bare domain without www."""

    def test_normal_url(self):
        assert extract_domain("https://example.com/path") == "example.com"

    def test_strips_www(self):
        assert extract_domain("https://www.example.com/page") == "example.com"

    def test_just_domain_no_path(self):
        assert extract_domain("https://example.com") == "example.com"

    def test_none_returns_empty_string(self):
        assert extract_domain(None) == ""

    def test_empty_string_returns_empty_string(self):
        assert extract_domain("") == ""

    def test_returns_lowercase(self):
        assert extract_domain("https://EXAMPLE.COM") == "example.com"


# ---------------------------------------------------------------------------
# trigram_similarity
# ---------------------------------------------------------------------------


class TestTrigramSimilarity:
    """trigram_similarity computes Jaccard similarity on character trigrams."""

    def test_identical_strings(self):
        assert trigram_similarity("hello world", "hello world") == 1.0

    def test_completely_different_strings(self):
        score = trigram_similarity("abcdef", "ghijklm")
        assert score == 0.0

    def test_similar_strings(self):
        score = trigram_similarity("nighttime", "daytime")
        # Shared trigrams include "ght", "hti", "tim", "ime", "met" etc.
        assert 0.0 < score < 1.0

    def test_empty_strings(self):
        assert trigram_similarity("", "hello") == 0.0
        assert trigram_similarity("hello", "") == 0.0
        assert trigram_similarity("", "") == 0.0

    def test_short_strings_no_trigrams(self):
        """Strings shorter than 3 chars have no trigrams → 0.0."""
        assert trigram_similarity("ab", "ab") == 0.0


# ---------------------------------------------------------------------------
# token_overlap_similarity
# ---------------------------------------------------------------------------


class TestTokenOverlapSimilarity:
    """token_overlap_similarity computes Jaccard similarity on word sets."""

    def test_identical_text(self):
        assert token_overlap_similarity("hello world", "hello world") == 1.0

    def test_no_shared_tokens(self):
        assert token_overlap_similarity("cats dogs", "apples oranges") == 0.0

    def test_partial_overlap(self):
        score = token_overlap_similarity("cats dogs birds", "cats dogs fish")
        # tokens1 = {cats, dogs, birds}, tokens2 = {cats, dogs, fish}
        # intersection = {cats, dogs} = 2, union = {cats, dogs, birds, fish} = 4
        assert score == pytest.approx(2 / 4)

    def test_empty_strings(self):
        assert token_overlap_similarity("", "hello") == 0.0
        assert token_overlap_similarity("hello", "") == 0.0
        assert token_overlap_similarity("", "") == 0.0

    def test_case_insensitive(self):
        assert token_overlap_similarity("Hello World", "hello world") == 1.0


# ---------------------------------------------------------------------------
# time_proximity
# ---------------------------------------------------------------------------


class TestTimeProximity:
    """time_proximity checks whether two datetimes fall within a window."""

    def test_within_default_window(self):
        dt1 = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        dt2 = datetime(2024, 6, 2, 8, 0, tzinfo=timezone.utc)
        # 20 hours apart, within default 24h window
        assert time_proximity(dt1, dt2) is True

    def test_outside_default_window(self):
        dt1 = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        dt2 = datetime(2024, 6, 3, 0, 0, tzinfo=timezone.utc)
        # 36 hours apart, outside default 24h window
        assert time_proximity(dt1, dt2) is False

    def test_none_inputs(self):
        assert time_proximity(None, None) is False
        assert time_proximity(None, datetime.now(tz=timezone.utc)) is False
        assert time_proximity(datetime.now(tz=timezone.utc), None) is False

    def test_custom_hours(self):
        dt1 = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        dt2 = datetime(2024, 6, 2, 0, 0, tzinfo=timezone.utc)
        # 12 hours apart
        assert time_proximity(dt1, dt2, hours=6) is False
        assert time_proximity(dt1, dt2, hours=24) is True

    def test_exact_boundary(self):
        dt1 = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        dt2 = dt1 + timedelta(hours=24)
        # Exactly 24 hours → within the ≤ window
        assert time_proximity(dt1, dt2, hours=24) is True


# ---------------------------------------------------------------------------
# compute_similarity
# ---------------------------------------------------------------------------


class TestComputeSimilarity:
    """compute_similarity returns a dict of similarity signals between two items."""

    def _make_item(
        self,
        url: str | None = "https://example.com/news/1",
        title: str | None = "Breaking Story",
        published_at: datetime | None = None,
    ) -> dict:
        if published_at is None:
            published_at = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        return {"url": url, "title": title, "published_at": published_at}

    def test_identical_items_high_score(self):
        item = self._make_item()
        result = compute_similarity(item, item)
        assert result["url_match"] is True
        assert result["domain_match"] is True
        assert result["title_similarity"] == 1.0
        assert result["time_proximate"] is True
        assert result["combined_score"] == pytest.approx(1.0)

    def test_same_url(self):
        item1 = self._make_item(url="https://example.com/news", title="Title A")
        item2 = self._make_item(url="https://example.com/news", title="Title B")
        result = compute_similarity(item1, item2)
        assert result["url_match"] is True

    def test_different_url(self):
        item1 = self._make_item(url="https://example.com/a", title="Title")
        item2 = self._make_item(url="https://other.com/b", title="Title")
        result = compute_similarity(item1, item2)
        assert result["url_match"] is False

    def test_same_domain(self):
        item1 = self._make_item(url="https://example.com/a", title="Title A")
        item2 = self._make_item(url="https://example.com/b", title="Title B")
        result = compute_similarity(item1, item2)
        assert result["domain_match"] is True

    def test_different_domain(self):
        item1 = self._make_item(url="https://example.com/a", title="Title")
        item2 = self._make_item(url="https://other.com/b", title="Title")
        result = compute_similarity(item1, item2)
        assert result["domain_match"] is False

    def test_within_time_window(self):
        dt1 = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        dt2 = datetime(2024, 6, 2, 8, 0, tzinfo=timezone.utc)
        item1 = self._make_item(published_at=dt1)
        item2 = self._make_item(published_at=dt2)
        result = compute_similarity(item1, item2)
        assert result["time_proximate"] is True

    def test_outside_time_window(self):
        dt1 = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        dt2 = datetime(2024, 6, 3, 0, 0, tzinfo=timezone.utc)
        item1 = self._make_item(published_at=dt1)
        item2 = self._make_item(published_at=dt2)
        result = compute_similarity(item1, item2)
        assert result["time_proximate"] is False

    def test_returns_all_expected_keys(self):
        item1 = self._make_item()
        item2 = self._make_item()
        result = compute_similarity(item1, item2)
        expected_keys = {
            "url_match",
            "title_similarity",
            "domain_match",
            "time_proximate",
            "combined_score",
        }
        assert set(result.keys()) == expected_keys

    def test_none_url_no_match(self):
        item1 = self._make_item(url=None, title="Hello")
        item2 = self._make_item(url=None, title="Hello")
        result = compute_similarity(item1, item2)
        assert result["url_match"] is False

    def test_none_title_similarity_zero(self):
        item1 = self._make_item(title=None)
        item2 = self._make_item(title=None)
        result = compute_similarity(item1, item2)
        assert result["title_similarity"] == 0.0

    def test_combined_score_weights(self):
        """Verify the combined score uses the documented weights."""
        # Same URL + same domain + same title + same time → all signals on
        item = self._make_item()
        result = compute_similarity(item, item)
        # 0.35 + 0.35 + 0.15 + 0.15 = 1.0
        assert result["combined_score"] == pytest.approx(1.0)

        # Only same domain + same time, different URL + different title
        item1 = self._make_item(url="https://example.com/a", title="Alpha")
        item2 = self._make_item(url="https://example.com/b", title="Beta")
        result = compute_similarity(item1, item2)
        # url_match=False(0) + title_sim(0) + domain_match=True(0.15) + time_prox(0.15)
        assert result["combined_score"] == pytest.approx(0.30)


# ---------------------------------------------------------------------------
# Near-duplicate detection — token overlap thresholds (Pass 4a)
# ---------------------------------------------------------------------------


class TestNearDuplicateTokenOverlap:
    """Verify token-overlap thresholds correctly identify near-duplicates."""

    def test_high_overlap_identified_as_near_duplicate(self):
        """Titles sharing most tokens should have high token overlap."""
        # 5 shared tokens out of 6 total unique → overlap ≈ 0.83
        score = token_overlap_similarity(
            "Company X Announces New CEO Today",
            "Company X Announces New Chief Executive Today",
        )
        assert score > 0.6  # above typical domain_title_threshold

    def test_low_overlap_not_near_duplicate(self):
        """Titles sharing few tokens should have low token overlap."""
        score = token_overlap_similarity(
            "Federal Reserve Raises Interest Rates",
            "Local Bakery Wins Pie Contest Award",
        )
        assert score == 0.0  # no shared tokens

    def test_partial_overlap_below_threshold(self):
        """Titles with some overlap but below clustering threshold."""
        score = token_overlap_similarity(
            "Market Update January 2024",
            "Market Update February 2025",
        )
        # Shared: {market, update} = 2; Union: {market, update, january, 2024, february, 2025} = 6
        # overlap = 2/6 ≈ 0.33
        assert score == pytest.approx(2 / 6, abs=0.01)
        assert score < 0.6  # below typical domain_title_threshold

    def test_trigram_catches_near_misspellings(self):
        """Trigram similarity catches titles that are slight variants."""
        # "CEO" vs "C.E.O." — trigrams will partially overlap
        score = trigram_similarity("Company CEO Resigns", "Company C.E.O. Resigns")
        assert 0.0 < score < 1.0  # some overlap but not exact

    def test_identical_titles_perfect_overlap(self):
        score = token_overlap_similarity(
            "Breaking News Story Today",
            "Breaking News Story Today",
        )
        assert score == 1.0

    def test_case_variation_preserves_overlap(self):
        score = token_overlap_similarity(
            "Breaking News Story",
            "breaking news story",
        )
        assert score == 1.0


# ---------------------------------------------------------------------------
# Syndication detection helpers (Pass 4a)
# ---------------------------------------------------------------------------


class TestSyndicationDetection:
    """Verify dedup utilities correctly handle syndicated content patterns."""

    def test_same_title_different_urls_fingerprint_match(self):
        """Syndicated stories with same title but different URLs share fingerprint."""
        fp1 = title_fingerprint("Tech Giant Reports Record Quarterly Earnings")
        fp2 = title_fingerprint("Tech Giant Reports Record Quarterly Earnings")
        assert fp1 == fp2

    def test_syndicated_title_with_minor_variations(self):
        """Syndicated titles often have minor outlet-specific additions."""
        # Exact match (fingerprint phase)
        fp1 = title_fingerprint("Oil Prices Surge to 6-Month High")
        fp2 = title_fingerprint("OIL PRICES SURGE TO 6-MONTH HIGH")
        assert fp1 == fp2

        # Minor variation → different fingerprint but similar tokens
        score = token_overlap_similarity(
            "Oil Prices Surge to 6-Month High",
            "Oil Prices Surge to Six Month High",
        )
        assert score > 0.6  # high token overlap (0.625)

    def test_different_content_no_false_syndication(self):
        """Truly different content should NOT match as syndicated."""
        score = token_overlap_similarity(
            "New Study Shows Coffee May Extend Lifespan",
            "Central Bank Signals Potential Rate Cut",
        )
        assert score == 0.0

    def test_syndication_across_tracking_params(self):
        """Syndicated via different tracking params should normalize to same URL."""
        url1 = "https://newswire.com/story?utm_source=twitter&utm_campaign=daily"
        url2 = "https://newswire.com/story?fbclid=abc123"
        url3 = "https://newswire.com/story"

        norm1 = normalize_url(url1)
        norm2 = normalize_url(url2)
        norm3 = normalize_url(url3)

        assert norm1 == norm2 == norm3 == "https://newswire.com/story"
