"""Tests for scoring.py pure utility functions."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.scoring import (
    _compute_decay_factor,
    compute_bm25_score,
    compute_combined_score,
    compute_competitor_mention_score,
    compute_competitor_mention_score_detailed,
    compute_content_type_prior_score,
    compute_document_frequencies,
    compute_excluded_topic_score,
    compute_freshness_score,
    compute_feed_health_score,
    compute_keyword_score,
    compute_keyword_score_detailed,
    compute_multi_signal_boost,
    compute_source_authority_score,
    decompose_theme,
    generate_competitor_aliases,
    normalize_competitor_name,
    normalize_theme,
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
        assert breakdown["weights"]["keyword"] == pytest.approx(0.30)
        assert breakdown["weights"]["competitor_mention"] == pytest.approx(0.20)
        assert breakdown["weights"]["freshness"] == pytest.approx(0.15)
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
        assert breakdown["weights"]["freshness"] == pytest.approx(0.15)
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

        assert breakdown["weights"]["keyword"] == pytest.approx(0.30)
        assert breakdown["weights"]["competitor_mention"] == pytest.approx(0.20)
        assert breakdown["weights"]["freshness"] == pytest.approx(0.15)
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


# ---------------------------------------------------------------------------
# Feed health scoring (Pass 4c)
# ---------------------------------------------------------------------------


class TestComputeFeedHealthScore:
    """compute_feed_health_score returns a weight based on feed reliability."""

    def test_no_data_returns_neutral(self):
        """Zero success rate (no fetches) → neutral 1.0."""
        assert compute_feed_health_score(0.0) == pytest.approx(1.0)

    def test_high_success_rate_full_weight(self):
        """>80% success rate → full weight 1.0."""
        assert compute_feed_health_score(0.90) == pytest.approx(1.0)
        assert compute_feed_health_score(0.81) == pytest.approx(1.0)
        assert compute_feed_health_score(1.0) == pytest.approx(1.0)

    def test_mid_success_rate_reduced_weight(self):
        """50-80% success rate → 0.8 weight."""
        assert compute_feed_health_score(0.50) == pytest.approx(0.8)
        assert compute_feed_health_score(0.65) == pytest.approx(0.8)
        assert compute_feed_health_score(0.80) == pytest.approx(0.8)

    def test_low_success_rate_low_weight(self):
        """<50% success rate → 0.5 weight."""
        assert compute_feed_health_score(0.49) == pytest.approx(0.5)
        assert compute_feed_health_score(0.0) == pytest.approx(1.0)  # special: no data
        assert compute_feed_health_score(0.01) == pytest.approx(0.5)

    def test_stale_feed_penalty(self):
        """Stale feed gets additional multiplicative penalty."""
        # Non-stale, high success → 1.0
        assert compute_feed_health_score(0.90, is_stale=False) == pytest.approx(1.0)
        # Stale, high success → 0.5 (1.0 * 0.5 stale penalty)
        assert compute_feed_health_score(0.90, is_stale=True) == pytest.approx(0.5)
        # Stale, mid success → 0.4 (0.8 * 0.5)
        assert compute_feed_health_score(0.65, is_stale=True) == pytest.approx(0.4)
        # Stale, low success → 0.25 (0.5 * 0.5)
        assert compute_feed_health_score(0.30, is_stale=True) == pytest.approx(0.25)

    def test_custom_thresholds(self):
        """Custom thresholds can be passed."""
        # With high_threshold=0.5 and mid_threshold=0.3
        # >50% → 1.0, 30-50% → 0.8, <30% → 0.5
        assert compute_feed_health_score(
            0.6, high_threshold=0.5, mid_threshold=0.3
        ) == pytest.approx(1.0)
        assert compute_feed_health_score(
            0.4, high_threshold=0.5, mid_threshold=0.3
        ) == pytest.approx(0.8)
        assert compute_feed_health_score(
            0.2, high_threshold=0.5, mid_threshold=0.3
        ) == pytest.approx(0.5)

    def test_custom_stale_penalty(self):
        """Custom stale penalty can be passed."""
        assert compute_feed_health_score(
            0.9, is_stale=True, stale_penalty=0.3
        ) == pytest.approx(0.3)
        assert compute_feed_health_score(
            0.9, is_stale=False, stale_penalty=0.3
        ) == pytest.approx(1.0)

    def test_score_clamped_to_zero_one(self):
        """Score is always clamped to [0, 1]."""
        score = compute_feed_health_score(0.01, is_stale=True, stale_penalty=10.0)
        assert 0.0 <= score <= 1.0


class TestFeedHealthInPipelineScoring:
    """Content from unreliable/stale feeds scores lower in pipeline scoring."""

    def _make_feed(self, db, ws_id, **overrides):
        """Helper to create a FeedSource with reliability tracking fields."""
        from app.models.feed import FeedSource

        defaults = {
            "workspace_id": ws_id,
            "name": "Test Feed",
            "url": "https://example.com/feed",
            "type": "rss",
            "status": "healthy",
            "consecutive_fetch_failures": 0,
            "total_fetch_count": 0,
        }
        defaults.update(overrides)
        feed = FeedSource(**defaults)
        db.add(feed)
        db.flush()
        return feed

    def test_unreliable_feed_content_scores_lower(self, db_session):
        """Content from a feed with low success rate should score lower."""
        ws = _make_workspace(db_session, priority_themes=["ai"])

        # Reliable feed (100% success, not stale)
        reliable_feed = self._make_feed(
            db_session,
            ws.id,
            name="Reliable Feed",
            total_fetch_count=10,
            consecutive_fetch_failures=0,
        )

        # Unreliable feed (33% success rate, not stale — only 2 consecutive failures,
        # total < threshold so is_stale=False)
        unreliable_feed = self._make_feed(
            db_session,
            ws.id,
            name="Unreliable Feed",
            total_fetch_count=3,
            consecutive_fetch_failures=2,
        )

        # Create identical items from each feed
        reliable_item = _make_item(
            db_session,
            ws.id,
            title="AI breakthrough announced today",
            feed_source_id=reliable_feed.id,
        )
        unreliable_item = _make_item(
            db_session,
            ws.id,
            title="AI breakthrough announced today",
            feed_source_id=unreliable_feed.id,
        )

        score_content_items(db_session, [reliable_item, unreliable_item], ws)

        # Reliable feed item should score higher
        assert reliable_item.final_score is not None
        assert unreliable_item.final_score is not None
        assert reliable_item.final_score > unreliable_item.final_score

        # Verify feed_health_weight appears in breakdown
        unreliable_breakdown = unreliable_item.score_breakdown_json
        assert "feed_health_weight" in unreliable_breakdown
        # 33% success rate → low tier → 0.5 weight
        assert unreliable_breakdown["feed_health_weight"] == pytest.approx(0.5)

    def test_stale_feed_content_scores_lower(self, db_session):
        """Content from a stale feed should score even lower."""
        ws = _make_workspace(db_session, priority_themes=["ai"])

        # Healthy feed (100% success, not stale)
        healthy_feed = self._make_feed(
            db_session,
            ws.id,
            name="Healthy Feed",
            total_fetch_count=10,
            consecutive_fetch_failures=0,
        )

        # Stale feed (high success rate but 5+ consecutive failures)
        # 90% success rate (9 successes, 1 stale period), 5 consecutive failures now
        stale_feed = self._make_feed(
            db_session,
            ws.id,
            name="Stale Feed",
            total_fetch_count=15,
            consecutive_fetch_failures=5,
        )

        healthy_item = _make_item(
            db_session,
            ws.id,
            title="AI advances in robotics",
            feed_source_id=healthy_feed.id,
        )
        stale_item = _make_item(
            db_session,
            ws.id,
            title="AI advances in robotics",
            feed_source_id=stale_feed.id,
        )

        score_content_items(db_session, [healthy_item, stale_item], ws)

        assert healthy_item.final_score is not None
        assert stale_item.final_score is not None
        assert healthy_item.final_score > stale_item.final_score

        # Stale feed should have aggressive penalty
        stale_breakdown = stale_item.score_breakdown_json
        assert "feed_health_weight" in stale_breakdown
        # High success rate (10/15 ≈ 0.67 → mid tier 0.8) but stale → 0.8 * 0.5 = 0.4
        assert stale_breakdown["feed_health_weight"] == pytest.approx(0.4)

    def test_no_feed_source_no_penalty(self, db_session):
        """Items without a feed_source_id should not be penalized."""
        ws = _make_workspace(db_session, priority_themes=["ai"])

        # Item with no feed association
        item = _make_item(
            db_session,
            ws.id,
            title="AI news",
            feed_source_id=None,
        )

        score_content_items(db_session, [item], ws)

        assert item.final_score is not None
        breakdown = item.score_breakdown_json
        # No feed_health_weight should appear when no feed
        assert "feed_health_weight" not in breakdown

    def test_feed_health_in_breakdown_scores(self, db_session):
        """feed_health appears in the scores section of the breakdown."""
        ws = _make_workspace(db_session, priority_themes=["ai"])

        feed = self._make_feed(
            db_session,
            ws.id,
            total_fetch_count=10,
            consecutive_fetch_failures=3,  # 70% success → mid tier (0.8)
        )

        item = _make_item(
            db_session,
            ws.id,
            title="AI article",
            feed_source_id=feed.id,
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        assert "feed_health" in breakdown["scores"]
        assert breakdown["scores"]["feed_health"] == pytest.approx(0.8)
        assert "feed_health_weight" in breakdown
        assert breakdown["feed_health_weight"] == pytest.approx(0.8)

    def test_stale_low_success_most_penalized(self, db_session):
        """Stale + low success rate = most aggressive penalty."""
        ws = _make_workspace(db_session, priority_themes=["ai"])

        # Stale + low success (<50%): weight = 0.5 * 0.5 = 0.25
        bad_feed = self._make_feed(
            db_session,
            ws.id,
            total_fetch_count=10,
            consecutive_fetch_failures=6,  # 40% success, and >=5 failures → stale
        )

        item = _make_item(
            db_session,
            ws.id,
            title="AI news from bad source",
            feed_source_id=bad_feed.id,
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        assert breakdown["feed_health_weight"] == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# BM25 multi-word priority theme repair (Pass 2b)
# ---------------------------------------------------------------------------


class TestBM25MultiWordTerms:
    """BM25 scoring handles multi-word priority themes correctly."""

    def test_bm25_multiword_term_matches_when_component_words_present(self):
        """A multi-word term like 'edge computing' scores > 0 when both
        component words appear in the text."""
        text = "Enterprise edge platforms are reshaping computing infrastructure"
        score = compute_bm25_score(text, ["edge computing"])
        assert score > 0.0

    def test_bm25_multiword_term_partial_match_scores_less_than_full_match(self):
        """A multi-word term gives partial credit when only some component words
        are present — scores > 0 but strictly less than when all words match."""
        partial_text = "The cutting edge of modern design"  # only "edge"
        full_text = "Enterprise edge platforms reshaping computing infrastructure"
        partial_score = compute_bm25_score(partial_text, ["edge computing"])
        full_score = compute_bm25_score(full_text, ["edge computing"])
        assert partial_score > 0.0
        assert full_score > partial_score

    def test_bm25_mixed_single_and_multiword_terms(self):
        """Both single-word and multi-word query terms contribute in the
        same score calculation."""
        text = "New ai breakthroughs improve cloud security measures"
        score = compute_bm25_score(text, ["ai", "cloud security"])
        assert score > 0.0

        # Verify each term individually also contributes
        score_ai_only = compute_bm25_score(text, ["cloud security"])
        score_cloud_only = compute_bm25_score(text, ["ai"])
        assert score_ai_only > 0.0
        assert score_cloud_only > 0.0

    def test_bm25_multiword_matching_case_insensitive(self):
        """Multi-word matching is case-insensitive."""
        text = "EDGE COMPUTING trends are accelerating"
        score = compute_bm25_score(text, ["edge computing"])
        assert score > 0.0

    def test_bm25_multiword_regression_with_batch_idf(self):
        """Multi-word terms produce non-zero BM25 when IDF is computed
        across a document batch."""
        items_texts = [
            "Enterprise edge platforms are reshaping computing infrastructure",
            "New fintech regulations announced today",
            "Sports results: football and basketball scores",
        ]
        query_terms = ["edge computing"]
        idf = compute_document_frequencies(items_texts, query_terms)

        # The first document should get a non-zero BM25 score
        score = compute_bm25_score(items_texts[0], query_terms, idf=idf)
        assert score > 0.0

        # Documents without matching words should score 0
        score_no_match = compute_bm25_score(items_texts[2], query_terms, idf=idf)
        assert score_no_match == pytest.approx(0.0)

    def test_score_content_items_multiword_priority_themes_contribute_bm25(
        self, db_session
    ):
        """Workspace with multi-word priority themes produces non-zero BM25
        in score breakdowns for matching content."""
        ws = _make_workspace(
            db_session,
            priority_themes=["edge computing", "cloud security"],
        )
        # Matching item — contains both "edge computing" and "cloud security"
        match_item = _make_item(
            db_session,
            ws.id,
            title="Enterprise edge platforms reshape computing infrastructure",
            summary_snippet="New advances in edge computing and cloud security "
            "are transforming the industry landscape.",
        )
        # Non-matching items — needed so IDF is non-zero for matching terms
        other_item1 = _make_item(
            db_session,
            ws.id,
            title="Local sports results from this weekend",
            summary_snippet="Football and basketball scores updated.",
        )
        other_item2 = _make_item(
            db_session,
            ws.id,
            title="Celebrity gossip and entertainment news",
            summary_snippet="Latest celebrity gossip and movie reviews.",
        )

        score_content_items(db_session, [match_item, other_item1, other_item2], ws)

        assert match_item.score_breakdown_json is not None
        assert match_item.score_breakdown_json["scores"]["bm25"] > 0


# ---------------------------------------------------------------------------
# Pass 1 — Baseline diagnostics and scoring observability
# ---------------------------------------------------------------------------


class TestScoreBreakdownConsistency:
    """Score breakdown dict always contains all expected component keys."""

    def test_score_breakdown_contains_component_scores_consistently(self, db_session):
        """Verify the score breakdown dict always contains all expected component keys.

        This test ensures backward compatibility: all existing component keys
        must be present in the breakdown regardless of workspace configuration.
        """
        ws = _make_workspace(
            db_session,
            priority_themes=["ai", "machine learning", "robotics"],
            competitors=["OpenAI", "Anthropic"],
        )
        item = _make_item(
            db_session,
            ws.id,
            title="OpenAI announces AI and machine learning breakthrough",
            url="https://reuters.com/tech/ai-breakthrough",
            content_type="news",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        assert breakdown is not None

        # Core component scores must always be present
        expected_score_keys = [
            "keyword",
            "competitor_mention",
            "freshness",
            "source_authority",
            "bm25",
            "content_type_prior",
        ]
        for key in expected_score_keys:
            assert key in breakdown["scores"], f"Missing score component: {key}"

        # Metadata keys must always be present
        expected_metadata_keys = [
            "weights",
            "combined_score",
            "excluded_topic_score",
            "filter_reason",
            "content_type",
            "theme_match",
            "competitor_match",
        ]
        for key in expected_metadata_keys:
            assert key in breakdown, f"Missing metadata key: {key}"

    def test_score_breakdown_consistent_with_no_themes(self, db_session):
        """Breakdown is consistent even with empty priority themes."""
        ws = _make_workspace(db_session, priority_themes=[], competitors=[])
        item = _make_item(db_session, ws.id, title="Some article")

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        assert "theme_match" in breakdown
        assert "matched" in breakdown["theme_match"]
        assert "unmatched" in breakdown["theme_match"]
        assert "normalized_themes" in breakdown["theme_match"]
        assert "competitor_match" in breakdown


class TestThemeMatchMetadata:
    """Score breakdown exposes theme match details for diagnostics."""

    def test_score_breakdown_can_expose_theme_match_metadata(self, db_session):
        """Theme match metadata shows which themes matched and which didn't."""
        ws = _make_workspace(
            db_session,
            priority_themes=[
                "ai",
                "machine learning",
                "quantum computing",
                "blockchain",
            ],
        )

        # Item matches "ai" and "machine learning" but not the others
        item = _make_item(
            db_session,
            ws.id,
            title="AI breakthrough in machine learning announced today",
            summary_snippet="New advances in artificial intelligence.",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        assert "theme_match" in breakdown

        theme_match = breakdown["theme_match"]
        assert "matched" in theme_match
        assert "unmatched" in theme_match
        assert "normalized_themes" in theme_match

        # "ai" and "machine learning" should be matched
        assert "ai" in theme_match["matched"]
        assert "machine learning" in theme_match["matched"]

        # "quantum computing" and "blockchain" should be unmatched
        assert "quantum computing" in theme_match["unmatched"]
        assert "blockchain" in theme_match["unmatched"]

        # Normalized themes should contain all themes (lowercased)
        assert set(theme_match["normalized_themes"]) == {
            "ai",
            "machine learning",
            "quantum computing",
            "blockchain",
        }

    def test_theme_match_all_matched(self, db_session):
        """When all themes match, unmatched list is empty."""
        ws = _make_workspace(db_session, priority_themes=["ai", "technology"])
        item = _make_item(db_session, ws.id, title="AI and technology news")

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        assert len(breakdown["theme_match"]["matched"]) == 2
        assert len(breakdown["theme_match"]["unmatched"]) == 0

    def test_theme_match_none_matched(self, db_session):
        """When no themes match, matched list is empty."""
        ws = _make_workspace(db_session, priority_themes=["quantum", "blockchain"])
        item = _make_item(db_session, ws.id, title="Weather forecast today")

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        assert len(breakdown["theme_match"]["matched"]) == 0
        assert len(breakdown["theme_match"]["unmatched"]) == 2

    def test_theme_match_case_insensitive(self, db_session):
        """Theme matching is case-insensitive in metadata."""
        ws = _make_workspace(
            db_session,
            priority_themes=["AI", "Machine Learning", "QUANTUM"],
        )
        item = _make_item(
            db_session,
            ws.id,
            title="ai and machine learning advances",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        # Normalized themes should be lowercased
        assert "ai" in breakdown["theme_match"]["normalized_themes"]
        assert "machine learning" in breakdown["theme_match"]["normalized_themes"]
        assert "quantum" in breakdown["theme_match"]["normalized_themes"]


class TestCompetitorMatchMetadata:
    """Score breakdown exposes competitor match details for diagnostics."""

    def test_score_breakdown_can_expose_competitor_match_metadata(self, db_session):
        """Competitor match metadata shows which competitors matched and which didn't."""
        ws = _make_workspace(
            db_session,
            competitors=["OpenAI", "Anthropic", "Google DeepMind"],
        )

        # Item mentions OpenAI but not the others
        item = _make_item(
            db_session,
            ws.id,
            title="OpenAI releases new GPT model",
            summary_snippet="OpenAI announced breakthrough capabilities.",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        assert "competitor_match" in breakdown

        comp_match = breakdown["competitor_match"]
        assert "matched" in comp_match
        assert "unmatched" in comp_match
        assert "normalized_competitors" in comp_match

        # "openai" should be matched
        assert "openai" in comp_match["matched"]

        # Others should be unmatched
        assert "anthropic" in comp_match["unmatched"]
        assert "google deepmind" in comp_match["unmatched"]

        # Normalized competitors should contain all competitors (lowercased)
        assert set(comp_match["normalized_competitors"]) == {
            "openai",
            "anthropic",
            "google deepmind",
        }

    def test_competitor_match_all_matched(self, db_session):
        """When all competitors are mentioned, unmatched list is empty."""
        ws = _make_workspace(db_session, competitors=["OpenAI", "Anthropic"])
        item = _make_item(
            db_session,
            ws.id,
            title="OpenAI and Anthropic collaborate on AI safety",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        assert len(breakdown["competitor_match"]["matched"]) == 2
        assert len(breakdown["competitor_match"]["unmatched"]) == 0

    def test_competitor_match_none_matched(self, db_session):
        """When no competitors are mentioned, matched list is empty."""
        ws = _make_workspace(db_session, competitors=["OpenAI", "Anthropic"])
        item = _make_item(db_session, ws.id, title="Weather forecast today")

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        assert len(breakdown["competitor_match"]["matched"]) == 0
        assert len(breakdown["competitor_match"]["unmatched"]) == 2

    def test_competitor_match_case_insensitive(self, db_session):
        """Competitor matching is case-insensitive in metadata."""
        ws = _make_workspace(db_session, competitors=["OpenAI", "ANTHROPIC"])
        item = _make_item(
            db_session,
            ws.id,
            title="openai is growing fast",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        # Normalized competitors should be lowercased
        assert "openai" in breakdown["competitor_match"]["normalized_competitors"]
        assert "anthropic" in breakdown["competitor_match"]["normalized_competitors"]


class TestComputeKeywordScoreDetailed:
    """compute_keyword_score_detailed returns score with match details."""

    def test_returns_tuple_with_matched_and_unmatched(self):
        score, matched, unmatched = compute_keyword_score_detailed(
            "AI and machine learning are growing",
            ["ai", "machine learning", "blockchain"],
        )
        assert score == pytest.approx(2 / 3)
        assert set(matched) == {"ai", "machine learning"}
        assert set(unmatched) == {"blockchain"}

    def test_all_matched(self):
        score, matched, unmatched = compute_keyword_score_detailed(
            "ai machine learning",
            ["ai", "machine learning"],
        )
        assert score == pytest.approx(1.0)
        assert len(matched) == 2
        assert len(unmatched) == 0

    def test_none_matched(self):
        score, matched, unmatched = compute_keyword_score_detailed(
            "weather forecast",
            ["ai", "crypto"],
        )
        assert score == pytest.approx(0.0)
        assert len(matched) == 0
        assert len(unmatched) == 2

    def test_empty_text_returns_zero_with_all_unmatched(self):
        score, matched, unmatched = compute_keyword_score_detailed("", ["ai"])
        assert score == pytest.approx(0.0)
        assert matched == []
        assert unmatched == ["ai"]

    def test_empty_keywords_returns_zero_with_empty_lists(self):
        score, matched, unmatched = compute_keyword_score_detailed("some text", [])
        assert score == pytest.approx(0.0)
        assert matched == []
        assert unmatched == []


class TestComputeCompetitorMentionScoreDetailed:
    """compute_competitor_mention_score_detailed returns score with match details."""

    def test_returns_tuple_with_matched_and_unmatched(self):
        score, matched, unmatched = compute_competitor_mention_score_detailed(
            "OpenAI announced a new model",
            ["OpenAI", "Anthropic", "Google"],
        )
        assert score == pytest.approx(1.0)
        assert set(matched) == {"openai"}
        assert set(unmatched) == {"anthropic", "google"}

    def test_all_matched(self):
        score, matched, unmatched = compute_competitor_mention_score_detailed(
            "OpenAI and Anthropic collaborate",
            ["OpenAI", "Anthropic"],
        )
        assert score == pytest.approx(1.0)
        assert len(matched) == 2
        assert len(unmatched) == 0

    def test_none_matched(self):
        score, matched, unmatched = compute_competitor_mention_score_detailed(
            "Weather forecast today",
            ["OpenAI", "Anthropic"],
        )
        assert score == pytest.approx(0.0)
        assert len(matched) == 0
        assert len(unmatched) == 2

    def test_empty_text_returns_zero_with_all_unmatched(self):
        score, matched, unmatched = compute_competitor_mention_score_detailed(
            "", ["OpenAI"]
        )
        assert score == pytest.approx(0.0)
        assert matched == []
        assert unmatched == ["openai"]

    def test_empty_competitors_returns_zero_with_empty_lists(self):
        score, matched, unmatched = compute_competitor_mention_score_detailed(
            "some text", []
        )
        assert score == pytest.approx(0.0)
        assert matched == []
        assert unmatched == []


# ---------------------------------------------------------------------------
# Pass 3 — Normalize profile themes and competitor aliases before scoring
# ---------------------------------------------------------------------------


class TestCompetitorNormalization:
    """Competitor name normalization strips noise and generates aliases."""

    def test_normalize_competitor_removes_parenthetical_noise(self):
        """Parenthetical annotations are stripped from competitor aliases."""
        raw = "Tenyo Metallic Nano (Japanese licensee, same factory)"
        aliases = generate_competitor_aliases(raw)
        # The base alias should have the parenthetical stripped
        assert "tenyo metallic nano" in aliases
        # No alias should contain the raw parenthetical content
        for alias in aliases:
            assert "(" not in alias
            assert "japanese licensee" not in alias

    def test_normalize_competitor_generates_expected_aliases(self):
        """generate_competitor_aliases produces meaningful matching aliases."""
        # Tenyo: full name, suffix (drop first word), first word
        aliases = generate_competitor_aliases(
            "Tenyo Metallic Nano (Japanese licensee, same factory)"
        )
        assert "tenyo metallic nano" in aliases
        assert "metallic nano" in aliases
        assert "tenyo" in aliases

        # Piececool: single word, no meaningful parenthetical phrase
        aliases = generate_competitor_aliases("Piececool (Chinese 3D metal puzzles)")
        assert "piececool" in aliases

        # UGEARS: single uppercase word
        aliases = generate_competitor_aliases(
            "UGEARS (Ukrainian wooden mechanical models)"
        )
        assert "ugears" in aliases

        # Fascinations: single word with a meaningful parenthetical phrase
        aliases = generate_competitor_aliases(
            "Fascinations (Metal Earth parent company)"
        )
        assert "fascinations" in aliases
        assert "metal earth" in aliases

    def test_aliases_are_deterministic(self):
        """Calling generate_competitor_aliases twice returns the same result."""
        name = "Tenyo Metallic Nano (Japanese licensee, same factory)"
        first = generate_competitor_aliases(name)
        second = generate_competitor_aliases(name)
        assert first == second

    def test_empty_input_returns_empty(self):
        assert normalize_competitor_name("") == ""
        assert normalize_competitor_name(None) == ""  # type: ignore[arg-type]
        assert generate_competitor_aliases("") == []
        assert generate_competitor_aliases(None) == []  # type: ignore[arg-type]

    def test_no_parenthetical_generates_base_and_word_aliases(self):
        """Competitor without parenthetical still generates suffix/first-word aliases."""
        aliases = generate_competitor_aliases("Metal Earth Models")
        assert "metal earth models" in aliases
        assert "earth models" in aliases
        assert "metal" in aliases

    def test_normalize_competitor_name_lowercases(self):
        assert normalize_competitor_name("OpenAI") == "openai"
        assert normalize_competitor_name("  SPACE  ") == "space"


class TestThemeDecomposition:
    """Theme decomposition splits complex theme strings into sub-terms."""

    def test_priority_theme_decomposition_generates_subterms(self):
        """decompose_theme splits comma-separated and and-separated themes."""
        # Comma-separated themes
        result = decompose_theme("Star Wars, Marvel, Disney franchise developments")
        assert "star wars" in result
        assert "marvel" in result

        # "and" split
        result = decompose_theme("licensed merchandise and IP deals")
        assert "licensed merchandise" in result
        assert "ip deals" in result

    def test_decomposition_generates_bigrams_for_long_phrases(self):
        """3+ word phrases produce bigram sub-terms."""
        result = decompose_theme("hobby retail channel and specialty store trends")
        assert "hobby retail channel" in result
        assert "specialty store trends" in result
        assert "hobby retail" in result
        assert "retail channel" in result
        assert "specialty store" in result

    def test_decomposition_is_deterministic(self):
        """decompose_theme always returns the same result for the same input."""
        theme = "Star Wars, Marvel, Disney franchise developments"
        assert decompose_theme(theme) == decompose_theme(theme)

    def test_empty_input_returns_empty(self):
        assert decompose_theme("") == []
        assert decompose_theme(None) == []  # type: ignore[arg-type]

    def test_single_word_theme_unchanged(self):
        assert decompose_theme("ai") == ["ai"]
        assert decompose_theme("hobby") == ["hobby"]

    def test_two_word_theme_unchanged(self):
        assert decompose_theme("star wars") == ["star wars"]

    def test_normalize_theme_lowercases(self):
        assert normalize_theme("Star Wars") == "star wars"
        assert normalize_theme("  SPACE  ") == "space"


class TestKeywordScoreWithNormalizedThemes:
    """Keyword scoring matches on decomposed sub-terms, not just raw strings."""

    def test_keyword_score_uses_normalized_theme_terms(self):
        """A comma-separated theme matches when any sub-term appears in text."""
        # The full raw string "Star Wars, Marvel" is NOT a substring of the
        # text, but "marvel" IS — so the keyword should still match.
        text = "New marvel movie announced this week"
        score = compute_keyword_score(text, ["Star Wars, Marvel"])
        assert score == pytest.approx(1.0)

    def test_keyword_score_detailed_with_decomposed_theme(self):
        """Detailed variant reports the theme as matched via sub-term."""
        text = "New marvel movie announced this week"
        score, matched, unmatched = compute_keyword_score_detailed(
            text, ["Star Wars, Marvel"]
        )
        assert score == pytest.approx(1.0)
        # The raw lowercased keyword is reported as matched
        assert "star wars, marvel" in matched

    def test_keyword_score_and_split_matches(self):
        """'and'-separated theme phrases are decomposed for matching."""
        text = "New IP deals announced in the licensing sector"
        score = compute_keyword_score(text, ["licensed merchandise and IP deals"])
        assert score == pytest.approx(1.0)

    def test_keyword_score_simple_themes_unaffected(self):
        """Simple single-word themes are unaffected by decomposition."""
        score = compute_keyword_score("AI is here", ["ai"])
        assert score == pytest.approx(1.0)
        score = compute_keyword_score("Weather today", ["ai"])
        assert score == pytest.approx(0.0)


class TestCompetitorMentionScoreWithAliases:
    """Competitor mention scoring matches on generated aliases."""

    def test_competitor_mention_score_uses_aliases_not_only_raw_strings(self):
        """Competitor with parenthetical matches on its base name via alias."""
        text = "Tenyo releases new metallic nano model kit"
        score = compute_competitor_mention_score(
            text,
            ["Tenyo Metallic Nano (Japanese licensee, same factory)"],
        )
        assert score == pytest.approx(1.0)

    def test_competitor_mention_matches_on_first_word_alias(self):
        """A competitor should match when only its first-word alias appears."""
        text = "Tenyo announced a new product line today"
        score = compute_competitor_mention_score(
            text,
            ["Tenyo Metallic Nano (Japanese licensee, same factory)"],
        )
        assert score == pytest.approx(1.0)

    def test_competitor_mention_matches_on_parenthetical_phrase(self):
        """A competitor should match via a capitalized phrase in parenthetical."""
        text = "Metal Earth is expanding its product range"
        score = compute_competitor_mention_score(
            text,
            ["Fascinations (Metal Earth parent company)"],
        )
        assert score == pytest.approx(1.0)

    def test_competitor_mention_detailed_with_aliases(self):
        """Detailed variant reports the competitor as matched via alias."""
        score, matched, unmatched = compute_competitor_mention_score_detailed(
            "Tenyo announces new product",
            ["Tenyo Metallic Nano (Japanese licensee, same factory)"],
        )
        assert score == pytest.approx(1.0)
        assert len(matched) == 1
        assert "tenyo metallic nano (japanese licensee, same factory)" in matched

    def test_competitor_mention_simple_names_unaffected(self):
        """Simple competitor names without parentheticals are unaffected."""
        score = compute_competitor_mention_score(
            "OpenAI announced a new model", ["OpenAI"]
        )
        assert score == pytest.approx(1.0)


class TestBM25WithNormalizedThemes:
    """BM25 scoring in the pipeline uses decomposed theme terms."""

    def test_bm25_uses_normalized_theme_terms(self, db_session):
        """BM25 score is non-zero when a decomposed sub-term matches."""
        ws = _make_workspace(
            db_session,
            priority_themes=["Star Wars, Marvel"],
        )
        # Item containing "marvel" but not the full raw theme string
        item = _make_item(
            db_session,
            ws.id,
            title="New Marvel superhero movie announced",
            content_type="news",
        )
        # Several non-matching items so IDF for "marvel" is non-zero
        # (IDF = log(N/(1+df)); with N=4, df=1 → log(4/2) = log(2) > 0)
        other_items = [
            _make_item(db_session, ws.id, title=title, content_type="news")
            for title in [
                "Weather forecast for this weekend",
                "Sports results and football scores",
                "Local politics update from city hall",
            ]
        ]

        score_content_items(db_session, [item] + other_items, ws)

        assert item.score_breakdown_json is not None
        assert item.score_breakdown_json["scores"]["bm25"] > 0

    def test_bm25_breakdown_includes_decomposed_themes(self, db_session):
        """Score breakdown includes decomposed_themes metadata."""
        ws = _make_workspace(
            db_session,
            priority_themes=["Star Wars, Marvel, Disney franchise developments"],
        )
        item = _make_item(
            db_session,
            ws.id,
            title="Some article",
            content_type="news",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        assert "theme_match" in breakdown
        assert "decomposed_themes" in breakdown["theme_match"]
        decomposed = breakdown["theme_match"]["decomposed_themes"]
        assert "star wars, marvel, disney franchise developments" in decomposed
        assert (
            "star wars"
            in decomposed["star wars, marvel, disney franchise developments"]
        )
        assert (
            "marvel" in decomposed["star wars, marvel, disney franchise developments"]
        )

    def test_competitor_aliases_in_breakdown(self, db_session):
        """Score breakdown includes competitor_aliases metadata."""
        ws = _make_workspace(
            db_session,
            competitors=["Fascinations (Metal Earth parent company)"],
        )
        item = _make_item(
            db_session,
            ws.id,
            title="Some article",
            content_type="news",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        assert "competitor_match" in breakdown
        assert "competitor_aliases" in breakdown["competitor_match"]
        aliases = breakdown["competitor_match"]["competitor_aliases"]
        raw_key = "fascinations (metal earth parent company)"
        assert raw_key in aliases
        assert "fascinations" in aliases[raw_key]
        assert "metal earth" in aliases[raw_key]


# ---------------------------------------------------------------------------
# Pass 4 — Scoring quality and weighting improvements
# ---------------------------------------------------------------------------


class TestComputeMultiSignalBoost:
    """compute_multi_signal_boost rewards articles matching multiple themes."""

    def test_single_theme_match_no_boost(self):
        boost, count = compute_multi_signal_boost(["star wars"])
        assert boost == pytest.approx(0.0)
        assert count == 1

    def test_two_theme_matches_gets_boost(self):
        boost, count = compute_multi_signal_boost(["star wars", "licensing"])
        assert boost == pytest.approx(0.05)
        assert count == 2

    def test_three_theme_matches_gets_boost(self):
        boost, count = compute_multi_signal_boost(
            ["star wars", "licensing", "toy industry"]
        )
        assert boost == pytest.approx(0.05)
        assert count == 3

    def test_empty_matched_themes_no_boost(self):
        boost, count = compute_multi_signal_boost([])
        assert boost == pytest.approx(0.0)
        assert count == 0

    def test_custom_bonus_and_threshold(self):
        boost, count = compute_multi_signal_boost(
            ["a", "b"], bonus=0.10, min_distinct_themes=2
        )
        assert boost == pytest.approx(0.10)

    def test_below_custom_threshold_no_boost(self):
        boost, count = compute_multi_signal_boost(
            ["a"], bonus=0.10, min_distinct_themes=3
        )
        assert boost == pytest.approx(0.0)


class TestPass4ScoringQuality:
    """Pass 4 scoring quality tests: realistic toy/licensing scenario."""

    def test_realistic_toy_licensing_article_scores_above_threshold(self, db_session):
        """A realistic toy/franchise/licensing article should score above 0.15."""
        ws = _make_workspace(
            db_session,
            priority_themes=[
                "licensed franchise",
                "collectibles",
                "toy industry",
                "Star Wars",
                "model kit",
            ],
            competitors=["Fascinations", "Piececool"],
        )
        item = _make_item(
            db_session,
            ws.id,
            title="Hasbro announces new Star Wars licensed collectible toy line",
            summary_snippet=(
                "Hasbro has signed a new licensing deal for Star Wars collectibles, "
                "expanding their toy industry portfolio with premium model kits."
            ),
            content_type="news",
        )

        score_content_items(db_session, [item], ws)

        assert item.final_score is not None
        assert item.final_score > 0.15, (
            f"Expected strong toy/licensing article to score > 0.15, got {item.final_score}"
        )

    def test_irrelevant_generic_licensing_article_scores_lower_than_toy_licensing_article(
        self, db_session
    ):
        """A generic licensing article should score lower than a toy-specific one."""
        ws = _make_workspace(
            db_session,
            priority_themes=[
                "licensed franchise",
                "collectibles",
                "toy industry",
                "Star Wars",
                "model kit",
            ],
        )
        # Strong toy-specific article
        strong_item = _make_item(
            db_session,
            ws.id,
            title="Hasbro announces new Star Wars licensed collectible toy line",
            summary_snippet=(
                "Hasbro has signed a new licensing deal for Star Wars collectibles, "
                "expanding their toy industry portfolio with premium model kits."
            ),
            content_type="news",
        )
        # Generic licensing article (matches "licensed franchise" but not toy themes)
        generic_item = _make_item(
            db_session,
            ws.id,
            title="New software licensing deal announced for enterprise cloud",
            summary_snippet=(
                "TechCorp has entered a licensing agreement for enterprise software, "
                "expanding their intellectual property portfolio."
            ),
            content_type="news",
        )

        score_content_items(db_session, [strong_item, generic_item], ws)

        assert strong_item.final_score is not None
        assert generic_item.final_score is not None
        assert strong_item.final_score > generic_item.final_score, (
            f"Expected strong article ({strong_item.final_score}) > "
            f"generic article ({generic_item.final_score})"
        )

    def test_competitor_article_scores_above_generic_noise_article(self, db_session):
        """An article mentioning a competitor should score above noise."""
        ws = _make_workspace(
            db_session,
            priority_themes=["model kit", "collectibles"],
            competitors=["Fascinations", "Piececool"],
        )
        competitor_item = _make_item(
            db_session,
            ws.id,
            title="Piececool releases new metal puzzle collection",
            summary_snippet="Piececool's new 3D metal puzzle series is now available.",
            content_type="news",
        )
        noise_item = _make_item(
            db_session,
            ws.id,
            title="Local weather forecast for the weekend",
            summary_snippet="Sunny skies expected throughout the weekend.",
            content_type="news",
        )

        score_content_items(db_session, [competitor_item, noise_item], ws)

        assert competitor_item.final_score is not None
        assert noise_item.final_score is not None
        assert competitor_item.final_score > noise_item.final_score, (
            f"Expected competitor article ({competitor_item.final_score}) > "
            f"noise article ({noise_item.final_score})"
        )

    def test_trusted_domain_boost_improves_source_authority(self, db_session):
        """Articles from trusted domains should get higher source authority."""
        ws = _make_workspace(
            db_session,
            priority_themes=["model kit"],
            trusted_domains=["toybook.com", "licenseglobal.com", "hasbro.com"],
        )
        trusted_item = _make_item(
            db_session,
            ws.id,
            title="New model kit announced",
            url="https://toybook.com/new-model-kit",
            content_type="news",
        )
        untrusted_item = _make_item(
            db_session,
            ws.id,
            title="New model kit announced",
            url="https://random-blog.xyz/new-model-kit",
            content_type="news",
        )

        score_content_items(db_session, [trusted_item, untrusted_item], ws)

        trusted_auth = trusted_item.score_breakdown_json["scores"]["source_authority"]
        untrusted_auth = untrusted_item.score_breakdown_json["scores"][
            "source_authority"
        ]
        assert trusted_auth == pytest.approx(1.0)
        assert untrusted_auth == pytest.approx(0.3)
        assert trusted_item.final_score > untrusted_item.final_score

    def test_multi_signal_article_scores_higher_than_single_signal_article(
        self, db_session
    ):
        """An article matching multiple themes should score higher than single-theme."""
        ws = _make_workspace(
            db_session,
            priority_themes=[
                "Star Wars",
                "model kit",
                "collectibles",
                "toy industry",
            ],
        )
        # Multi-signal: matches Star Wars, model kit, collectibles
        multi_item = _make_item(
            db_session,
            ws.id,
            title="New Star Wars model kit collectible announced",
            summary_snippet="A new Star Wars collectible model kit is coming soon.",
            content_type="news",
        )
        # Single-signal: only matches model kit
        single_item = _make_item(
            db_session,
            ws.id,
            title="New model kit available for purchase",
            summary_snippet="A new model kit is now available.",
            content_type="news",
        )

        score_content_items(db_session, [multi_item, single_item], ws)

        assert multi_item.final_score is not None
        assert single_item.final_score is not None
        assert multi_item.final_score > single_item.final_score, (
            f"Expected multi-signal article ({multi_item.final_score}) > "
            f"single-signal article ({single_item.final_score})"
        )

        # Verify the multi-signal boost appears in the breakdown
        breakdown = multi_item.score_breakdown_json
        assert "multi_signal_boost" in breakdown
        assert breakdown["multi_signal_boost"]["bonus"] == pytest.approx(0.05)

    def test_metalearth_regression_distribution_not_compressed_to_trivial_range(
        self, db_session
    ):
        """Strong articles should score significantly higher than weak ones.

        Uses a synthetic corpus (no network) with four archetypes:
        - Strong toy/franchise/licensing article
        - Generic licensing article
        - Competitor article
        - Weak/noisy article
        """
        ws = _make_workspace(
            db_session,
            priority_themes=[
                "metal earth",
                "model kit",
                "collectibles",
                "Star Wars",
                "toy industry",
                "licensed franchise",
            ],
            competitors=["Fascinations", "Piececool", "UGEARS"],
        )

        # Strong article: hits multiple priority themes
        strong = _make_item(
            db_session,
            ws.id,
            title=(
                "Hasbro and Disney announce new Star Wars licensed franchise "
                "collectible model kit series"
            ),
            summary_snippet=(
                "The new Star Wars collectible model kit series from Hasbro and Disney "
                "brings iconic spacecraft to the toy industry. These premium licensed "
                "franchise collectibles expand the metal earth market."
            ),
            content_type="news",
        )

        # Generic licensing: only partially relevant
        generic = _make_item(
            db_session,
            ws.id,
            title="New software licensing agreement for enterprise cloud platform",
            summary_snippet=(
                "TechCorp announced a new licensing deal for cloud computing, "
                "expanding their intellectual property portfolio in enterprise."
            ),
            content_type="news",
        )

        # Competitor article
        competitor = _make_item(
            db_session,
            ws.id,
            title="Piececool releases new 3D metal puzzle architecture series",
            summary_snippet="Piececool's new architecture model kit collection is available.",
            content_type="news",
        )

        # Weak/noisy article
        weak = _make_item(
            db_session,
            ws.id,
            title="Local sports results: football and basketball scores updated",
            summary_snippet="Weekend sports roundup with all the latest scores.",
            content_type="news",
        )

        score_content_items(db_session, [strong, generic, competitor, weak], ws)

        scores = {
            "strong": strong.final_score,
            "generic": generic.final_score,
            "competitor": competitor.final_score,
            "weak": weak.final_score,
        }

        # All scores should be non-None
        for name, score in scores.items():
            assert score is not None, f"{name} score should not be None"

        # Strong should be significantly higher than weak
        assert scores["strong"] > scores["weak"], (
            f"Strong ({scores['strong']}) should exceed weak ({scores['weak']})"
        )

        # The score range should not be compressed to a trivial band.
        # We check that the gap between strong and weak is at least 0.1.
        gap = scores["strong"] - scores["weak"]
        assert gap >= 0.1, (
            f"Score gap between strong ({scores['strong']}) and weak "
            f"({scores['weak']}) is {gap:.4f}, expected >= 0.1"
        )

        # Strong should also beat generic and competitor
        assert scores["strong"] > scores["generic"]
        assert scores["competitor"] > scores["weak"]
