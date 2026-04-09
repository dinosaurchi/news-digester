"""Tests for scoring.py pure utility functions."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.scoring import (
    compute_bm25_score,
    compute_combined_score,
    compute_competitor_mention_score,
    compute_excluded_topic_score,
    compute_freshness_score,
    compute_keyword_score,
    compute_source_authority_score,
)


# ---------------------------------------------------------------------------
# compute_keyword_score
# ---------------------------------------------------------------------------


class TestComputeKeywordScore:
    """compute_keyword_score returns a normalised keyword match ratio."""

    def test_all_keywords_match(self):
        score = compute_keyword_score(
            "AI and machine learning are growing",
            ["ai", "machine learning"],
        )
        assert score == pytest.approx(1.0)

    def test_partial_keyword_match(self):
        score = compute_keyword_score(
            "AI is transforming the industry",
            ["ai", "blockchain"],
        )
        assert score == pytest.approx(0.5)

    def test_no_keywords_match(self):
        score = compute_keyword_score(
            "The weather is sunny today",
            ["ai", "crypto"],
        )
        assert score == pytest.approx(0.0)

    def test_case_insensitive(self):
        score = compute_keyword_score("OPENAI released GPT", ["openai", "gpt"])
        assert score == pytest.approx(1.0)

    def test_empty_keywords_returns_zero(self):
        assert compute_keyword_score("some text", []) == 0.0

    def test_empty_text_returns_zero(self):
        assert compute_keyword_score("", ["ai"]) == 0.0

    def test_none_text_returns_zero(self):
        assert compute_keyword_score(None, ["ai"]) == 0.0  # type: ignore[arg-type]

    def test_single_keyword_matches(self):
        score = compute_keyword_score("sustainability report", ["sustainability"])
        assert score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# compute_competitor_mention_score
# ---------------------------------------------------------------------------


class TestComputeCompetitorMentionScore:
    """compute_competitor_mention_score detects competitor name mentions."""

    def test_mention_found(self):
        score = compute_competitor_mention_score(
            "OpenAI announced a new model", ["OpenAI"]
        )
        assert score == pytest.approx(1.0)

    def test_mention_case_insensitive(self):
        score = compute_competitor_mention_score("openai is growing fast", ["OpenAI"])
        assert score == pytest.approx(1.0)

    def test_partial_word_match(self):
        score = compute_competitor_mention_score("OpenAI's revenue soared", ["OpenAI"])
        assert score == pytest.approx(1.0)

    def test_no_mention(self):
        score = compute_competitor_mention_score(
            "Google released a new feature", ["OpenAI", "Anthropic"]
        )
        assert score == pytest.approx(0.0)

    def test_multiple_competitors_one_match(self):
        score = compute_competitor_mention_score(
            "Microsoft invests in AI", ["Google", "Microsoft", "Apple"]
        )
        assert score == pytest.approx(1.0)

    def test_empty_competitors_returns_zero(self):
        assert compute_competitor_mention_score("some text", []) == 0.0

    def test_empty_text_returns_zero(self):
        assert compute_competitor_mention_score("", ["OpenAI"]) == 0.0


# ---------------------------------------------------------------------------
# compute_excluded_topic_score
# ---------------------------------------------------------------------------


class TestComputeExcludedTopicScore:
    """compute_excluded_topic_score flags content matching excluded topics."""

    def test_excluded_topic_found(self):
        score = compute_excluded_topic_score(
            "Celebrity gossip about famous actors",
            ["celebrity gossip", "sports"],
        )
        assert score == pytest.approx(1.0)

    def test_excluded_topic_not_found(self):
        score = compute_excluded_topic_score(
            "New AI regulation proposed",
            ["celebrity gossip", "sports"],
        )
        assert score == pytest.approx(0.0)

    def test_case_insensitive(self):
        score = compute_excluded_topic_score(
            "ENTERTAINMENT NEWS today",
            ["entertainment"],
        )
        assert score == pytest.approx(1.0)

    def test_empty_excluded_topics_returns_zero(self):
        assert compute_excluded_topic_score("some text", []) == 0.0

    def test_empty_text_returns_zero(self):
        assert compute_excluded_topic_score("", ["sports"]) == 0.0

    def test_multiple_excluded_one_match(self):
        score = compute_excluded_topic_score(
            "Sports results and football highlights",
            ["celebrity", "sports", "gaming"],
        )
        assert score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# compute_freshness_score
# ---------------------------------------------------------------------------


class TestComputeFreshnessScore:
    """compute_freshness_score returns a linear-decay recency score."""

    def test_just_published(self):
        now = datetime.now(timezone.utc)
        score = compute_freshness_score(now)
        assert score == pytest.approx(1.0)

    def test_half_age(self):
        now = datetime.now(timezone.utc)
        published = now - timedelta(hours=84)  # half of 168
        score = compute_freshness_score(published, max_age_hours=168.0)
        assert score == pytest.approx(0.5, abs=0.05)

    def test_max_age(self):
        now = datetime.now(timezone.utc)
        published = now - timedelta(hours=168)
        score = compute_freshness_score(published, max_age_hours=168.0)
        assert score == pytest.approx(0.0, abs=0.05)

    def test_older_than_max_age(self):
        now = datetime.now(timezone.utc)
        published = now - timedelta(hours=200)
        score = compute_freshness_score(published, max_age_hours=168.0)
        assert score == pytest.approx(0.0)

    def test_none_published_at_returns_neutral(self):
        score = compute_freshness_score(None)
        assert score == pytest.approx(0.5)

    def test_naive_datetime(self):
        """Naive datetimes are treated as UTC."""
        now = datetime.now(timezone.utc)
        naive = now.replace(tzinfo=None)
        score = compute_freshness_score(naive)
        assert score == pytest.approx(1.0)

    def test_custom_max_age(self):
        now = datetime.now(timezone.utc)
        published = now - timedelta(hours=12)
        score = compute_freshness_score(published, max_age_hours=24.0)
        assert score == pytest.approx(0.5, abs=0.05)

    def test_future_date(self):
        """A future publish date returns 1.0."""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)
        score = compute_freshness_score(future)
        assert score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# compute_source_authority_score
# ---------------------------------------------------------------------------


class TestComputeSourceAuthorityScore:
    """compute_source_authority_score checks domain trust."""

    def test_trusted_domain(self):
        score = compute_source_authority_score(
            "reuters.com", ["reuters.com", "bbc.com"]
        )
        assert score == pytest.approx(1.0)

    def test_trusted_domain_case_insensitive(self):
        score = compute_source_authority_score(
            "Reuters.COM", ["reuters.com", "bbc.com"]
        )
        assert score == pytest.approx(1.0)

    def test_untrusted_domain(self):
        score = compute_source_authority_score(
            "random-blog.com", ["reuters.com", "bbc.com"]
        )
        assert score == pytest.approx(0.3)

    def test_no_trusted_domains_neutral(self):
        score = compute_source_authority_score("example.com", [])
        assert score == pytest.approx(0.5)

    def test_none_trusted_domains_neutral(self):
        score = compute_source_authority_score("example.com", None)
        assert score == pytest.approx(0.5)

    def test_empty_domain_untrusted(self):
        score = compute_source_authority_score("", ["reuters.com"])
        assert score == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# compute_bm25_score
# ---------------------------------------------------------------------------


class TestComputeBm25Score:
    """compute_bm25_score returns a simplified BM25-style score."""

    def test_query_terms_present(self):
        score = compute_bm25_score("ai machine learning ai", ["ai", "learning"])
        assert score > 0.0

    def test_no_query_terms_match(self):
        score = compute_bm25_score("weather forecast today", ["blockchain", "crypto"])
        assert score == pytest.approx(0.0)

    def test_empty_query_terms(self):
        score = compute_bm25_score("some text", [])
        assert score == pytest.approx(0.0)

    def test_empty_text(self):
        score = compute_bm25_score("", ["ai"])
        assert score == pytest.approx(0.0)

    def test_higher_frequency_higher_score(self):
        """A term appearing more often should contribute more."""
        low = compute_bm25_score("ai is here", ["ai"])
        high = compute_bm25_score("ai ai ai ai ai ai", ["ai"])
        assert high > low

    def test_multiple_terms_accumulate(self):
        single = compute_bm25_score("ai machine", ["ai"])
        multiple = compute_bm25_score("ai machine", ["ai", "machine"])
        assert multiple >= single

    def test_case_insensitive(self):
        score = compute_bm25_score("AI ML", ["ai", "ml"])
        assert score > 0.0

    def test_score_bounded_by_one(self):
        score = compute_bm25_score("word " * 100, ["word"])
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# compute_combined_score
# ---------------------------------------------------------------------------


class TestComputeCombinedScore:
    """compute_combined_score returns a weighted sum with breakdown."""

    def test_all_scores_one(self):
        scores = {
            "keyword": 1.0,
            "competitor_mention": 1.0,
            "freshness": 1.0,
            "source_authority": 1.0,
            "bm25": 1.0,
        }
        combined, breakdown = compute_combined_score(scores)
        assert combined == pytest.approx(1.0)

    def test_all_scores_zero(self):
        scores = {
            "keyword": 0.0,
            "competitor_mention": 0.0,
            "freshness": 0.0,
            "source_authority": 0.0,
            "bm25": 0.0,
        }
        combined, breakdown = compute_combined_score(scores)
        assert combined == pytest.approx(0.0)

    def test_missing_keys_default_to_zero(self):
        combined, breakdown = compute_combined_score({})
        assert combined == pytest.approx(0.0)
        for key in [
            "keyword",
            "competitor_mention",
            "freshness",
            "source_authority",
            "bm25",
        ]:
            assert breakdown["scores"][key] == 0.0

    def test_partial_scores(self):
        scores = {"keyword": 1.0, "freshness": 1.0}
        combined, breakdown = compute_combined_score(scores)
        # keyword=0.25*1.0 + competitor_mention=0.20*0 + freshness=0.20*1.0
        # + source_authority=0.15*0 + bm25=0.20*0 = 0.45
        assert combined == pytest.approx(0.45)

    def test_breakdown_contains_weights(self):
        _, breakdown = compute_combined_score({})
        assert "weights" in breakdown
        assert breakdown["weights"]["keyword"] == pytest.approx(0.25)
        assert breakdown["weights"]["competitor_mention"] == pytest.approx(0.20)
        assert breakdown["weights"]["freshness"] == pytest.approx(0.20)
        assert breakdown["weights"]["source_authority"] == pytest.approx(0.15)
        assert breakdown["weights"]["bm25"] == pytest.approx(0.20)

    def test_breakdown_contains_combined_score(self):
        combined, breakdown = compute_combined_score({"keyword": 0.5})
        assert "combined_score" in breakdown
        assert breakdown["combined_score"] == combined

    def test_breakdown_is_json_serialisable(self):
        """The breakdown dict should be safe to pass to json.dumps."""
        import json

        scores = {"keyword": 0.8, "bm25": 0.6}
        _, breakdown = compute_combined_score(scores)
        # Should not raise
        json.dumps(breakdown)

    def test_weights_sum_to_one(self):
        _, breakdown = compute_combined_score({})
        total = sum(breakdown["weights"].values())
        assert total == pytest.approx(1.0)
