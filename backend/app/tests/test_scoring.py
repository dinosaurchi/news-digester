"""Tests for scoring.py pure utility functions."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.scoring import (
    _compute_decay_factor,
    compute_bm25_score,
    compute_combined_score,
    compute_content_type_prior_score,
    compute_document_frequencies,
    compute_competitor_mention_score,
    compute_excluded_topic_score,
    compute_freshness_score,
    compute_keyword_score,
    compute_source_authority_score,
    score_content_items,
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


# ---------------------------------------------------------------------------
# score_content_items (pipeline-level scoring)
# ---------------------------------------------------------------------------


def _make_workspace(
    db,
    *,
    priority_themes=None,
    competitors=None,
    excluded_topics=None,
    trusted_domains=None,
    min_relevance_score=0.1,
    scoring_weights=None,
):
    """Helper to create a workspace with optional profile/settings."""
    from app.models.workspace import Workspace, WorkspaceProfile, WorkspaceSettings

    ws = Workspace(name="Test", customer="TestCo")
    db.add(ws)
    db.flush()

    profile = WorkspaceProfile(
        workspace_id=ws.id,
        priority_themes=priority_themes or [],
        competitors=competitors or [],
        excluded_topics=excluded_topics or [],
    )
    db.add(profile)

    thresholds: dict = {"min_relevance_score": min_relevance_score}
    if trusted_domains is not None:
        thresholds["trusted_domains"] = trusted_domains
    if scoring_weights is not None:
        thresholds["scoring_weights"] = scoring_weights

    settings = WorkspaceSettings(
        workspace_id=ws.id,
        thresholds=thresholds,
    )
    db.add(settings)
    db.flush()
    return ws


def _make_item(db, ws_id, **overrides):
    """Helper to create a ContentItem with sensible defaults."""
    from app.models.content import ContentItem

    defaults = {
        "workspace_id": ws_id,
        "title": "Generic news article about technology",
        "url": "https://example.com/article",
        "source_name": "Example News",
        "content_type": "news",
        "summary_snippet": "A summary about technology trends.",
        "published_at": datetime.now(timezone.utc),
        "status": "pending",
    }
    defaults.update(overrides)
    item = ContentItem(**defaults)
    db.add(item)
    db.flush()
    return item


class TestScoreContentItems:
    """score_content_items ties scoring utilities to real ContentItem objects."""

    def test_basic_scoring_with_themes(self, db_session):
        ws = _make_workspace(
            db_session,
            priority_themes=["ai", "machine learning"],
        )
        item = _make_item(
            db_session,
            ws.id,
            title="AI breakthrough in machine learning",
            summary_snippet="New advances in AI and ML are reshaping industries.",
        )

        result = score_content_items(db_session, [item], ws)

        assert result["included_count"] == 1
        assert result["excluded_count"] == 0
        assert item.status == "included"
        assert item.final_score is not None
        assert item.final_score > 0
        assert item.score_breakdown_json is not None
        assert "combined_score" in item.score_breakdown_json
        assert "filter_reason" in item.score_breakdown_json

    def test_excluded_by_topic(self, db_session):
        ws = _make_workspace(
            db_session,
            priority_themes=["ai"],
            excluded_topics=["celebrity gossip"],
        )
        item = _make_item(
            db_session,
            ws.id,
            title="Celebrity gossip: latest drama unfolds",
            summary_snippet="All the celebrity gossip you need.",
        )

        result = score_content_items(db_session, [item], ws)

        assert result["excluded_count"] == 1
        assert result["included_count"] == 0
        assert item.status == "excluded"
        assert item.exclusion_reason == "matched_excluded_topic"
        assert item.score_breakdown_json["filter_reason"] == "matched_excluded_topic"
        assert item.score_breakdown_json["excluded_topic_score"] == 1.0

    def test_excluded_by_low_score(self, db_session):
        ws = _make_workspace(
            db_session,
            priority_themes=["quantum computing"],
            min_relevance_score=0.5,
        )
        item = _make_item(
            db_session,
            ws.id,
            title="Weather forecast for tomorrow",
            summary_snippet="Sunny skies expected.",
        )

        result = score_content_items(db_session, [item], ws)

        assert result["excluded_count"] == 1
        assert item.status == "excluded"
        assert item.exclusion_reason == "below_relevance_threshold"

    def test_no_workspace_profile(self, db_session):
        """Should work even when workspace has no profile at all."""
        from app.models.workspace import Workspace

        ws = Workspace(name="NoProfile", customer="TestCo")
        db_session.add(ws)
        db_session.flush()

        item = _make_item(db_session, ws.id, title="Some article")

        result = score_content_items(db_session, [item], ws)

        # With no themes, keyword and bm25 scores are 0, but freshness and
        # source_authority still contribute. The item may be included or
        # excluded depending on the threshold.
        assert result["included_count"] + result["excluded_count"] == 1
        assert item.final_score is not None
        assert item.score_breakdown_json is not None

    def test_no_workspace_settings(self, db_session):
        """Should use defaults when workspace has no settings."""
        from app.models.workspace import Workspace, WorkspaceProfile

        ws = Workspace(name="NoSettings", customer="TestCo")
        db_session.add(ws)
        db_session.flush()

        profile = WorkspaceProfile(
            workspace_id=ws.id,
            priority_themes=["ai"],
        )
        db_session.add(profile)
        db_session.flush()

        item = _make_item(
            db_session,
            ws.id,
            title="AI news today",
            summary_snippet="Advances in artificial intelligence.",
        )

        result = score_content_items(db_session, [item], ws)

        # Should use default min_relevance_score of 0.1
        assert item.final_score is not None
        assert item.score_breakdown_json is not None

    def test_empty_items_list(self, db_session):
        ws = _make_workspace(db_session)

        result = score_content_items(db_session, [], ws)

        assert result["included_count"] == 0
        assert result["excluded_count"] == 0
        assert result["avg_score"] == 0.0
        assert result["min_score"] == 0.0
        assert result["max_score"] == 0.0

    def test_item_with_none_fields(self, db_session):
        """Handle items with missing summary, url, published_at."""
        ws = _make_workspace(db_session, priority_themes=["ai"])

        item = _make_item(
            db_session,
            ws.id,
            title="",  # empty string (title is NOT NULL in DB)
            summary_snippet=None,
            url=None,
            published_at=None,
        )

        # Should not raise
        result = score_content_items(db_session, [item], ws)

        assert result["included_count"] + result["excluded_count"] == 1
        assert item.final_score is not None

    def test_summary_metadata(self, db_session):
        ws = _make_workspace(db_session, priority_themes=["ai"])
        items = [
            _make_item(db_session, ws.id, title=f"Article {i} about AI")
            for i in range(3)
        ]

        result = score_content_items(db_session, items, ws)

        assert result["included_count"] + result["excluded_count"] == 3
        assert 0.0 <= result["avg_score"] <= 1.0
        assert 0.0 <= result["min_score"] <= 1.0
        assert 0.0 <= result["max_score"] <= 1.0
        assert result["min_score"] <= result["max_score"]

    def test_competitor_mention_detected(self, db_session):
        ws = _make_workspace(
            db_session,
            priority_themes=["ai"],
            competitors=["OpenAI"],
        )
        item = _make_item(
            db_session,
            ws.id,
            title="OpenAI releases new model",
            summary_snippet="OpenAI has announced a breakthrough.",
        )

        score_content_items(db_session, [item], ws)

        assert item.score_breakdown_json is not None
        assert item.score_breakdown_json["scores"][
            "competitor_mention"
        ] == pytest.approx(1.0)

    def test_trusted_domain_boost(self, db_session):
        ws = _make_workspace(
            db_session,
            priority_themes=["ai"],
            trusted_domains=["reuters.com"],
        )
        item = _make_item(
            db_session,
            ws.id,
            title="AI news",
            url="https://reuters.com/ai-article",
        )

        score_content_items(db_session, [item], ws)

        assert item.score_breakdown_json is not None
        assert item.score_breakdown_json["scores"]["source_authority"] == pytest.approx(
            1.0
        )

    def test_breakdown_contains_all_components(self, db_session):
        ws = _make_workspace(db_session, priority_themes=["ai"])
        item = _make_item(db_session, ws.id, title="AI article")

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        assert "weights" in breakdown
        assert "scores" in breakdown
        assert "combined_score" in breakdown
        assert "excluded_topic_score" in breakdown
        assert "filter_reason" in breakdown
        for key in [
            "keyword",
            "competitor_mention",
            "freshness",
            "source_authority",
            "bm25",
        ]:
            assert key in breakdown["scores"]

    def test_excluded_topic_takes_priority_over_low_score(self, db_session):
        """Excluded topic should be flagged even if score would be low anyway."""
        ws = _make_workspace(
            db_session,
            priority_themes=["quantum"],
            excluded_topics=["gossip"],
            min_relevance_score=0.5,
        )
        item = _make_item(
            db_session,
            ws.id,
            title="Celebrity gossip roundup",
            summary_snippet="The latest gossip from Hollywood.",
        )

        score_content_items(db_session, [item], ws)

        assert item.status == "excluded"
        assert item.exclusion_reason == "matched_excluded_topic"
        assert item.score_breakdown_json["filter_reason"] == "matched_excluded_topic"


# ---------------------------------------------------------------------------
# Configurable scoring weight overrides (Pass 1)
# ---------------------------------------------------------------------------


class TestWeightOverrides:
    """compute_combined_score supports optional weight overrides."""

    def test_valid_overrides_merge_with_defaults(self):
        scores = {
            "keyword": 1.0,
            "competitor_mention": 0.0,
            "freshness": 0.0,
            "source_authority": 0.0,
            "bm25": 0.0,
        }
        overrides = {"keyword": 0.50, "bm25": 0.25}
        combined, breakdown = compute_combined_score(scores, weight_overrides=overrides)

        assert breakdown["weights"]["keyword"] == pytest.approx(0.50)
        assert breakdown["weights"]["bm25"] == pytest.approx(0.25)
        # Unchanged keys keep their defaults
        assert breakdown["weights"]["competitor_mention"] == pytest.approx(0.20)
        assert breakdown["weights"]["freshness"] == pytest.approx(0.20)
        assert breakdown["weights"]["source_authority"] == pytest.approx(0.15)

    def test_unknown_weight_keys_are_ignored(self):
        scores = {"keyword": 1.0, "freshness": 0.0, "bm25": 0.0}
        overrides = {"keyword": 0.30, "bogus_key": 0.99, "another_unknown": 0.5}
        _, breakdown = compute_combined_score(scores, weight_overrides=overrides)

        assert "bogus_key" not in breakdown["weights"]
        assert "another_unknown" not in breakdown["weights"]
        # keyword was still updated
        assert breakdown["weights"]["keyword"] == pytest.approx(0.30)

    def test_no_overrides_uses_defaults(self):
        scores = {"keyword": 1.0}
        _, breakdown = compute_combined_score(scores, weight_overrides=None)

        assert breakdown["weights"]["keyword"] == pytest.approx(0.25)
        assert breakdown["weights"]["competitor_mention"] == pytest.approx(0.20)
        assert breakdown["weights"]["freshness"] == pytest.approx(0.20)
        assert breakdown["weights"]["source_authority"] == pytest.approx(0.15)
        assert breakdown["weights"]["bm25"] == pytest.approx(0.20)

    def test_score_breakdown_shows_which_weights_were_used(self):
        """The breakdown JSON contains the active weights dict."""
        overrides = {"freshness": 0.40, "source_authority": 0.10}
        _, breakdown = compute_combined_score({}, weight_overrides=overrides)

        # The weights in the breakdown should reflect the overrides
        assert breakdown["weights"]["freshness"] == pytest.approx(0.40)
        assert breakdown["weights"]["source_authority"] == pytest.approx(0.10)
        # Should be JSON-serialisable
        import json

        serialized = json.dumps(breakdown)
        assert "freshness" in serialized


# ---------------------------------------------------------------------------
# Feedback decay factor (Pass 2)
# ---------------------------------------------------------------------------


class TestComputeDecayFactor:
    """_compute_decay_factor returns exponential time decay."""

    def test_today_returns_approx_one(self):
        now = datetime.now(timezone.utc)
        factor = _compute_decay_factor(now)
        assert factor == pytest.approx(1.0)

    def test_30_days_ago_returns_approx_half(self):
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        factor = _compute_decay_factor(thirty_days_ago, half_life_days=30.0)
        assert factor == pytest.approx(0.5, abs=0.05)

    def test_90_plus_days_returns_negligible(self):
        ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)
        factor = _compute_decay_factor(ninety_days_ago, half_life_days=30.0)
        # 2^(-90/30) = 2^(-3) = 0.125
        assert factor == pytest.approx(0.125, abs=0.05)
        assert factor < 0.2

    def test_none_returns_zero(self):
        factor = _compute_decay_factor(None)
        assert factor == pytest.approx(0.0)

    def test_future_date_returns_one(self):
        future = datetime.now(timezone.utc) + timedelta(days=10)
        factor = _compute_decay_factor(future)
        assert factor == pytest.approx(1.0)

    def test_naive_datetime_treated_as_utc(self):
        now = datetime.now(timezone.utc)
        naive = now.replace(tzinfo=None)
        factor = _compute_decay_factor(naive)
        assert factor == pytest.approx(1.0)

    def test_custom_half_life(self):
        ten_days_ago = datetime.now(timezone.utc) - timedelta(days=10)
        factor = _compute_decay_factor(ten_days_ago, half_life_days=10.0)
        assert factor == pytest.approx(0.5, abs=0.05)


# ---------------------------------------------------------------------------
# BM25 with IDF (Pass 6)
# ---------------------------------------------------------------------------


class TestComputeDocumentFrequencies:
    """compute_document_frequencies computes IDF values for query terms."""

    def test_basic_idf_computation(self):
        items_texts = ["ai machine learning", "ai finance", "blockchain technology"]
        idf = compute_document_frequencies(items_texts, ["ai", "blockchain"])

        # "ai" appears in 2 of 3 documents → lower IDF
        assert "ai" in idf
        # "blockchain" appears in 1 of 3 documents → higher IDF
        assert "blockchain" in idf
        assert idf["blockchain"] > idf["ai"]

    def test_common_terms_have_lower_idf(self):
        items_texts = [
            "the market is up",
            "the market trends",
            "the market analysis",
            "ai breakthrough today",
        ]
        idf = compute_document_frequencies(items_texts, ["the", "ai"])

        # "the" appears in 3 docs, "ai" in 1 → "ai" should have higher IDF
        assert idf["ai"] > idf["the"]

    def test_empty_inputs_return_empty(self):
        assert compute_document_frequencies([], ["ai"]) == {}
        assert compute_document_frequencies(["text"], []) == {}
        assert compute_document_frequencies([], []) == {}

    def test_all_terms_absent_have_positive_idf(self):
        items_texts = ["banana apple cherry", "date fig grape"]
        idf = compute_document_frequencies(items_texts, ["zebra"])

        # "zebra" in 0 docs → idf = log(2 / (1+0)) = log(2) > 0
        assert idf["zebra"] > 0


class TestBM25WithIDF:
    """compute_bm25_score supports optional IDF weighting."""

    def test_with_idf_gives_different_result_than_without(self):
        text = "ai ai ai ai ai machine"
        query = ["ai", "machine"]

        score_without = compute_bm25_score(text, query, idf=None)
        # Very low IDF for the frequent term "ai", normal for "machine"
        idf = {"ai": 0.01, "machine": 1.0}
        score_with = compute_bm25_score(text, query, idf=idf)

        # With IDF, "ai" (frequent) is almost eliminated, reducing the score
        assert score_with != score_without
        assert score_with < score_without

    def test_without_idf_behaves_like_before(self):
        """When idf=None, the function behaves identically to the original TF-only mode."""
        text = "ai machine learning"
        query = ["ai", "machine"]
        score = compute_bm25_score(text, query, idf=None)
        assert score > 0.0

        # Manually verify: tf(ai)=1, tf(machine)=1
        # raw = (log(2) + log(2)) / 2 = log(2) ≈ 0.693 / 2 * ...
        # Just verify it matches calling with idf=None explicitly vs implicitly
        score_implicit = compute_bm25_score(text, query)
        assert score == score_implicit

    def test_idf_only_for_matching_terms(self):
        """IDF for terms not in text should have no effect."""
        text = "ai news"
        query = ["ai", "blockchain"]
        idf = {"ai": 1.0, "blockchain": 100.0}

        score = compute_bm25_score(text, query, idf=idf)
        # "blockchain" doesn't appear in text, so its IDF shouldn't inflate the score
        # Only "ai" contributes
        assert score > 0.0
        # The score should not be dominated by the "blockchain" IDF since it doesn't match
        assert score < 1.0

    def test_zero_idf_dampens_term(self):
        """A term with IDF=0 should not contribute to the score."""
        text = "ai machine"
        query = ["ai", "machine"]
        idf = {"ai": 0.0, "machine": 1.0}

        score = compute_bm25_score(text, query, idf=idf)
        # Only "machine" contributes since "ai" IDF is 0
        # Expected: log(2)*1.0 / 2 = 0.347
        assert score == pytest.approx(0.347, abs=0.05)


# ---------------------------------------------------------------------------
# Content type prior scoring (Pass 4a)
# ---------------------------------------------------------------------------


class TestComputeContentTypePriorScore:
    """compute_content_type_prior_score returns a prior based on content type."""

    def test_news_gets_highest_prior(self):
        score = compute_content_type_prior_score("news")
        assert score == pytest.approx(1.0)

    def test_blog_gets_lower_prior(self):
        score = compute_content_type_prior_score("blog")
        assert score == pytest.approx(0.7)

    def test_forum_gets_lowest_prior(self):
        score = compute_content_type_prior_score("forum")
        assert score == pytest.approx(0.5)

    def test_unknown_type_gets_neutral(self):
        score = compute_content_type_prior_score("podcast")
        assert score == pytest.approx(0.5)

    def test_none_returns_neutral(self):
        score = compute_content_type_prior_score(None)
        assert score == pytest.approx(0.5)

    def test_empty_string_returns_neutral(self):
        score = compute_content_type_prior_score("")
        assert score == pytest.approx(0.5)

    def test_case_insensitive(self):
        score = compute_content_type_prior_score("NEWS")
        assert score == pytest.approx(1.0)
        score = compute_content_type_prior_score("Blog")
        assert score == pytest.approx(0.7)

    def test_custom_weights_override_defaults(self):
        custom = {"news": 0.5, "blog": 1.0}
        assert compute_content_type_prior_score(
            "news", weights=custom
        ) == pytest.approx(0.5)
        assert compute_content_type_prior_score(
            "blog", weights=custom
        ) == pytest.approx(1.0)
        # Unknown types still get neutral
        assert compute_content_type_prior_score(
            "forum", weights=custom
        ) == pytest.approx(0.5)

    def test_competitor_and_press_release(self):
        assert compute_content_type_prior_score("competitor") == pytest.approx(0.8)
        assert compute_content_type_prior_score("press_release") == pytest.approx(0.9)

    def test_social_type(self):
        assert compute_content_type_prior_score("social") == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# Score breakdown includes all components (Pass 4a regression)
# ---------------------------------------------------------------------------


class TestScoreBreakdownAllComponents:
    """Score breakdown JSON includes all component signals including content_type_prior."""

    def test_breakdown_includes_content_type_prior(self, db_session):
        ws = _make_workspace(db_session, priority_themes=["ai"])
        item = _make_item(
            db_session,
            ws.id,
            title="AI article",
            content_type="news",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        assert "scores" in breakdown
        assert "content_type_prior" in breakdown["scores"]
        assert breakdown["scores"]["content_type_prior"] == pytest.approx(1.0)

    def test_breakdown_includes_content_type(self, db_session):
        ws = _make_workspace(db_session, priority_themes=["ai"])
        item = _make_item(
            db_session,
            ws.id,
            title="AI article",
            content_type="blog",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        assert "content_type" in breakdown
        assert breakdown["content_type"] == "blog"

    def test_content_type_prior_influences_score_when_weighted(self, db_session):
        """When content_type_prior has non-zero weight, it affects combined score."""
        from app.models.workspace import WorkspaceSettings

        ws = _make_workspace(
            db_session,
            priority_themes=["metal earth"],
            # Pass scoring weights + content type weights via settings
            scoring_weights={
                "keyword": 0.20,
                "competitor_mention": 0.15,
                "freshness": 0.15,
                "source_authority": 0.10,
                "bm25": 0.15,
                "content_type_prior": 0.25,
            },
        )

        # Override the existing settings to add content_type_weights
        existing_settings = (
            db_session.query(WorkspaceSettings)
            .filter(WorkspaceSettings.workspace_id == ws.id)
            .first()
        )
        thresholds = existing_settings.thresholds or {}
        thresholds["content_type_weights"] = {"news": 1.0, "blog": 0.3}
        existing_settings.thresholds = thresholds
        db_session.flush()

        # News item about metal earth
        news_item = _make_item(
            db_session,
            ws.id,
            title="New Metal Earth model announced",
            content_type="news",
        )
        # Blog item about metal earth (same keywords but lower content type prior)
        blog_item = _make_item(
            db_session,
            ws.id,
            title="New Metal Earth model announced",
            content_type="blog",
        )

        score_content_items(db_session, [news_item, blog_item], ws)

        # Both have identical keyword/bm25 scores, but news should score higher
        # because content_type_prior(news)=1.0 > content_type_prior(blog)=0.3
        assert news_item.final_score > blog_item.final_score

    def test_all_score_components_present_in_breakdown(self, db_session):
        """Verify every scoring component is present in the breakdown dict."""
        ws = _make_workspace(
            db_session,
            priority_themes=["ai", "robotics"],
            competitors=["OpenAI"],
        )
        item = _make_item(
            db_session,
            ws.id,
            title="OpenAI launches new AI and robotics initiative",
            url="https://reuters.com/tech/ai-robotics",
            content_type="press_release",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        # All individual score components
        for key in [
            "keyword",
            "competitor_mention",
            "freshness",
            "source_authority",
            "bm25",
            "content_type_prior",
        ]:
            assert key in breakdown["scores"], f"Missing score component: {key}"

        # Metadata fields
        assert "combined_score" in breakdown
        assert "weights" in breakdown
        assert "excluded_topic_score" in breakdown
        assert "filter_reason" in breakdown
        assert "content_type" in breakdown

        # content_type_prior should reflect press_release default
        assert breakdown["scores"]["content_type_prior"] == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# Metal Earth regression test fixture (Pass 4a)
# ---------------------------------------------------------------------------


def _make_metal_earth_workspace(db):
    """Create a Metal Earth-like workspace for regression testing.

    Simulates a hobby/collectibles business that sells metal model kits
    (licensed franchises, collectibles, aviation, architecture themes).
    """
    from app.models.workspace import Workspace, WorkspaceProfile, WorkspaceSettings

    ws = Workspace(name="Metal Earth Models", customer="MetalEarthCo")
    db.add(ws)
    db.flush()

    profile = WorkspaceProfile(
        workspace_id=ws.id,
        business_name="Metal Earth Models",
        description="Specialist retailer of Metal Earth 3D metal model kits",
        priority_themes=[
            "metal earth",
            "3d model",
            "model kit",
            "licensed franchise",
            "collectibles",
            "hobby",
            "aviation model",
            "architecture model",
            "star wars",
            "marvel",
            "DIY craft",
        ],
        competitors=["Fascinations", "MetalCraft", "HobbyBoss"],
        excluded_topics=[
            "celebrity gossip",
            "sports results",
            "real estate",
            "cryptocurrency",
        ],
    )
    db.add(profile)

    settings = WorkspaceSettings(
        workspace_id=ws.id,
        thresholds={
            "min_relevance_score": 0.15,
            "scoring_weights": {
                "keyword": 0.25,
                "competitor_mention": 0.15,
                "freshness": 0.15,
                "source_authority": 0.10,
                "bm25": 0.15,
                "content_type_prior": 0.20,
            },
            "content_type_weights": {
                "news": 1.0,
                "press_release": 0.95,
                "blog": 0.8,
                "competitor": 0.9,
                "forum": 0.6,
                "social": 0.3,
            },
            "trusted_domains": ["reuters.com", "bbc.com", "techcrunch.com"],
        },
    )
    db.add(settings)
    db.flush()
    return ws


class TestMetalEarthRegression:
    """Metal Earth workspace: themed content scores higher than irrelevant content."""

    def test_themed_content_scores_higher_than_irrelevant(self, db_session):
        ws = _make_metal_earth_workspace(db_session)

        # Themed content items
        themed_items = [
            _make_item(
                db_session,
                ws.id,
                title="New Metal Earth Star Wars Millennium Falcon kit announced",
                content_type="news",
                url="https://reuters.com/lifestyle/metal-earth-star-wars",
            ),
            _make_item(
                db_session,
                ws.id,
                title="Fascinations releases new 3D architecture model series",
                content_type="press_release",
                url="https://fascinations.com/press/architecture-models",
            ),
            _make_item(
                db_session,
                ws.id,
                title="Hobby enthusiasts review best DIY metal model kits 2024",
                content_type="blog",
                url="https://hobbyblog.com/best-metal-models",
            ),
        ]

        # Irrelevant content items
        irrelevant_items = [
            _make_item(
                db_session,
                ws.id,
                title="Celebrity gossip roundup: who wore what at the gala",
                content_type="news",
                url="https://gossipsite.com/celebrity-gala",
            ),
            _make_item(
                db_session,
                ws.id,
                title="Bitcoin reaches new all-time high as crypto surges",
                content_type="news",
                url="https://cryptonews.com/bitcoin-surge",
            ),
        ]

        all_items = themed_items + irrelevant_items
        score_content_items(db_session, all_items, ws)

        themed_scores = [item.final_score for item in themed_items]
        irrelevant_scores = [item.final_score for item in irrelevant_items]

        # Every themed item should score higher than every irrelevant item
        for ts in themed_scores:
            for irs in irrelevant_scores:
                assert ts is not None and irs is not None, "Scores should not be None"
                assert ts > irs, f"Themed score {ts} should be > irrelevant score {irs}"

    def test_competitor_mention_detected_in_metal_earth_context(self, db_session):
        ws = _make_metal_earth_workspace(db_session)

        item = _make_item(
            db_session,
            ws.id,
            title="Fascinations announces partnership with Disney for new model kits",
            content_type="news",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        assert breakdown["scores"]["competitor_mention"] == pytest.approx(1.0)

    def test_excluded_topic_drift_penalized(self, db_session):
        """Obvious topic drift (excluded topics) should be excluded."""
        ws = _make_metal_earth_workspace(db_session)

        crypto_item = _make_item(
            db_session,
            ws.id,
            title="Cryptocurrency market analysis: Bitcoin and Ethereum trends",
            content_type="news",
        )

        score_content_items(db_session, [crypto_item], ws)

        assert crypto_item.status == "excluded"
        assert crypto_item.exclusion_reason == "matched_excluded_topic"

    def test_trusted_domain_boost_in_metal_earth_context(self, db_session):
        ws = _make_metal_earth_workspace(db_session)

        reuters_item = _make_item(
            db_session,
            ws.id,
            title="New DIY craft trend: metal model building gains popularity",
            content_type="news",
            url="https://reuters.com/lifestyle/diy-craft-trend",
        )
        unknown_item = _make_item(
            db_session,
            ws.id,
            title="New DIY craft trend: metal model building gains popularity",
            content_type="news",
            url="https://random-blog.xyz/diy-craft-trend",
        )

        score_content_items(db_session, [reuters_item, unknown_item], ws)

        # Reuters item should have higher source_authority
        reuters_auth = reuters_item.score_breakdown_json["scores"]["source_authority"]
        unknown_auth = unknown_item.score_breakdown_json["scores"]["source_authority"]
        assert reuters_auth > unknown_auth

    def test_multiple_themes_accumulate_score(self, db_session):
        """Content matching multiple priority themes should score higher."""
        ws = _make_metal_earth_workspace(db_session)

        single_theme = _make_item(
            db_session,
            ws.id,
            title="New model kit available",
            content_type="news",
        )
        multi_theme = _make_item(
            db_session,
            ws.id,
            title="New Metal Earth 3D model kit combines Star Wars and aviation themes",
            content_type="news",
        )

        score_content_items(db_session, [single_theme, multi_theme], ws)

        assert multi_theme.final_score > single_theme.final_score
