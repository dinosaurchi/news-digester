"""Integration tests for Metal Earth scoring quality.

These tests exercise the full scoring pipeline end-to-end with realistic
Metal Earth-like data. They use a synthetic corpus (no network/real data
needed) and test through the scoring functions directly (not through the
live HTTP API).

Usage:
    cd backend && python -m pytest ../tests/integration/test_metalearth_scoring_api.py -v

Or from repo root:
    cd backend && python -m pytest ../tests/integration/test_metalearth_scoring_api.py -v
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.scoring import score_content_items


# ---------------------------------------------------------------------------
# Helpers — Metal Earth workspace and content item factories
# ---------------------------------------------------------------------------


def _make_metal_earth_workspace(
    db,
    *,
    priority_themes=None,
    competitors=None,
    excluded_topics=None,
    trusted_domains=None,
    min_relevance_score=0.15,
    scoring_weights=None,
    content_type_weights=None,
):
    """Create a Metal Earth-like workspace for integration testing.

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
        priority_themes=priority_themes
        or [
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
            "toy industry",
        ],
        competitors=competitors
        or [
            "Fascinations",
            "Piececool",
            "UGEARS",
            "MetalCraft",
            "HobbyBoss",
            "Tenyo Metallic Nano (Japanese licensee, same factory)",
        ],
        excluded_topics=excluded_topics
        or [
            "celebrity gossip",
            "sports results",
            "real estate",
            "cryptocurrency",
        ],
    )
    db.add(profile)

    thresholds: dict = {"min_relevance_score": min_relevance_score}
    if trusted_domains is not None:
        thresholds["trusted_domains"] = trusted_domains
    if scoring_weights is not None:
        thresholds["scoring_weights"] = scoring_weights
    if content_type_weights is not None:
        thresholds["content_type_weights"] = content_type_weights

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
        "title": "Generic news article",
        "url": "https://example.com/article",
        "source_name": "Example News",
        "content_type": "news",
        "summary_snippet": "A summary of the article.",
        "published_at": datetime.now(timezone.utc),
        "status": "pending",
    }
    defaults.update(overrides)
    item = ContentItem(**defaults)
    db.add(item)
    db.flush()
    return item


# ---------------------------------------------------------------------------
# Test a: Strong franchise licensing article scores above threshold
# ---------------------------------------------------------------------------


class TestStrongFranchiseLicensingArticle:
    """Strong franchise/licensing articles should score above the inclusion threshold."""

    def test_strong_franchise_licensing_article_scores_above_threshold(
        self, db_session
    ):
        """Star Wars toy licensing deal with Hasbro should score > 0.15."""
        ws = _make_metal_earth_workspace(db_session)

        # Create a synthetic article about Star Wars toy licensing deal with Hasbro
        item = _make_item(
            db_session,
            ws.id,
            title=(
                "Hasbro announces new Star Wars licensed franchise "
                "collectible model kit series"
            ),
            summary_snippet=(
                "Hasbro has signed a major licensing deal with Disney for Star Wars "
                "collectibles, expanding their toy industry portfolio with premium "
                "metal earth model kits. The new series features iconic spacecraft "
                "and vehicles from the beloved franchise."
            ),
            content_type="news",
            url="https://toybook.com/hasbro-star-wars-model-kits",
        )

        score_content_items(db_session, [item], ws)

        assert item.final_score is not None, "Final score should not be None"
        assert item.final_score > 0.15, (
            f"Star Wars toy licensing article should score > 0.15, got {item.final_score}"
        )
        assert item.status == "included", (
            f"Article should be included, got status={item.status}"
        )


# ---------------------------------------------------------------------------
# Test b: Generic unrelated licensing article scores lower
# ---------------------------------------------------------------------------


class TestGenericUnrelatedLicensingArticle:
    """Generic/unrelated licensing articles should score lower than franchise articles."""

    def test_generic_unrelated_licensing_article_scores_lower(self, db_session):
        """Pharmaceutical licensing deal should score lower than toy franchise article."""
        ws = _make_metal_earth_workspace(db_session)

        # Strong franchise article
        franchise_item = _make_item(
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
            url="https://toybook.com/star-wars-model-kits",
        )

        # Generic unrelated licensing article (pharmaceutical)
        pharma_item = _make_item(
            db_session,
            ws.id,
            title="Pfizer announces new pharmaceutical licensing deal for cancer drug",
            summary_snippet=(
                "Pfizer has entered a licensing agreement with a biotech startup "
                "for a new oncology treatment. The deal expands their intellectual "
                "property portfolio in the pharmaceutical sector."
            ),
            content_type="news",
            url="https://reuters.com/business/pfizer-licensing-deal",
        )

        score_content_items(db_session, [franchise_item, pharma_item], ws)

        assert franchise_item.final_score is not None
        assert pharma_item.final_score is not None
        assert franchise_item.final_score > pharma_item.final_score, (
            f"Franchise article ({franchise_item.final_score}) should score higher "
            f"than pharmaceutical licensing article ({pharma_item.final_score})"
        )


# ---------------------------------------------------------------------------
# Test c: Competitor article with alias match scores above noise
# ---------------------------------------------------------------------------


class TestCompetitorAliasMatch:
    """Articles mentioning competitor aliases should score above noise."""

    def test_competitor_article_with_alias_match_scores_above_noise(self, db_session):
        """Piececool (competitor alias) article should score higher than noise."""
        ws = _make_metal_earth_workspace(db_session)

        # Article mentioning Piececool (competitor alias)
        competitor_item = _make_item(
            db_session,
            ws.id,
            title="Piececool releases new Star Wars metal puzzle collection",
            summary_snippet=(
                "Piececool's new Star Wars 3D metal puzzle series features iconic "
                "spacecraft and vehicles. The collectible model kits are now available "
                "for hobbyists and Star Wars fans."
            ),
            content_type="news",
            url="https://hobbynews.com/piececool-star-wars",
        )

        # Noise article with no relevant terms
        noise_item = _make_item(
            db_session,
            ws.id,
            title="Local weather forecast for the weekend",
            summary_snippet=(
                "Sunny skies expected throughout the weekend with mild temperatures. "
                "No rain is forecast for the region."
            ),
            content_type="news",
            url="https://weathernews.com/weekend-forecast",
        )

        score_content_items(db_session, [competitor_item, noise_item], ws)

        assert competitor_item.final_score is not None
        assert noise_item.final_score is not None
        assert competitor_item.final_score > noise_item.final_score, (
            f"Competitor article ({competitor_item.final_score}) should score higher "
            f"than noise article ({noise_item.final_score})"
        )

    def test_competitor_alias_tenyo_matches(self, db_session):
        """Article mentioning 'Tenyo' should match via competitor alias."""
        ws = _make_metal_earth_workspace(db_session)

        # Article mentioning just "Tenyo" (first-word alias)
        item = _make_item(
            db_session,
            ws.id,
            title="Tenyo announces new metallic nano product line",
            summary_snippet="Tenyo expands its product range with new releases.",
            content_type="news",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        assert breakdown["scores"]["competitor_mention"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Test d: Score breakdown exposes theme, competitor, source diagnostics
# ---------------------------------------------------------------------------


class TestScoreBreakdownDiagnostics:
    """Score breakdown should contain all diagnostic keys for observability."""

    def test_score_breakdown_exposes_theme_competitor_source_diagnostics(
        self, db_session
    ):
        """Score breakdown must contain theme_match, competitor_match, multi_signal_boost."""
        ws = _make_metal_earth_workspace(db_session)

        # Realistic article that matches multiple themes
        item = _make_item(
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
            url="https://toybook.com/star-wars-model-kits",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        assert breakdown is not None, "Score breakdown should not be None"

        # Verify theme_match is present with expected structure
        assert "theme_match" in breakdown, "theme_match should be in breakdown"
        theme_match = breakdown["theme_match"]
        assert "matched" in theme_match
        assert "unmatched" in theme_match
        assert "normalized_themes" in theme_match

        # Verify competitor_match is present with expected structure
        assert "competitor_match" in breakdown, (
            "competitor_match should be in breakdown"
        )
        comp_match = breakdown["competitor_match"]
        assert "matched" in comp_match
        assert "unmatched" in comp_match
        assert "normalized_competitors" in comp_match
        assert "competitor_aliases" in comp_match

        # Verify multi_signal_boost is present (article matches multiple themes)
        assert "multi_signal_boost" in breakdown, (
            "multi_signal_boost should be in breakdown for multi-theme article"
        )
        assert breakdown["multi_signal_boost"]["bonus"] > 0
        assert breakdown["multi_signal_boost"]["distinct_matched_themes"] >= 2

    def test_score_breakdown_exposes_all_component_scores(self, db_session):
        """All individual score components must be present in breakdown."""
        ws = _make_metal_earth_workspace(db_session)

        item = _make_item(
            db_session,
            ws.id,
            title="New model kit announced",
            content_type="news",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        scores = breakdown["scores"]

        expected_keys = [
            "keyword",
            "competitor_mention",
            "freshness",
            "source_authority",
            "bm25",
            "content_type_prior",
        ]
        for key in expected_keys:
            assert key in scores, f"Missing score component: {key}"


# ---------------------------------------------------------------------------
# Test e: Trusted domain gets authority boost
# ---------------------------------------------------------------------------


class TestTrustedDomainAuthorityBoost:
    """Articles from trusted domains should get higher source authority."""

    def test_content_with_trusted_domain_gets_authority_boost(self, db_session):
        """Same article from trusted domain should have higher source_authority."""
        ws = _make_metal_earth_workspace(
            db_session,
            trusted_domains=["toybook.com", "licenseglobal.com", "hasbro.com"],
        )

        # Same article from trusted domain
        trusted_item = _make_item(
            db_session,
            ws.id,
            title="New Star Wars model kit announced",
            summary_snippet="A new Star Wars collectible model kit is coming soon.",
            content_type="news",
            url="https://toybook.com/star-wars-model-kit",
        )

        # Same article from untrusted domain
        untrusted_item = _make_item(
            db_session,
            ws.id,
            title="New Star Wars model kit announced",
            summary_snippet="A new Star Wars collectible model kit is coming soon.",
            content_type="news",
            url="https://random-blog.xyz/star-wars-model-kit",
        )

        score_content_items(db_session, [trusted_item, untrusted_item], ws)

        trusted_breakdown = trusted_item.score_breakdown_json
        untrusted_breakdown = untrusted_item.score_breakdown_json

        trusted_auth = trusted_breakdown["scores"]["source_authority"]
        untrusted_auth = untrusted_breakdown["scores"]["source_authority"]

        assert trusted_auth == pytest.approx(1.0), (
            f"Trusted domain should have source_authority=1.0, got {trusted_auth}"
        )
        assert untrusted_auth == pytest.approx(0.3), (
            f"Untrusted domain should have source_authority=0.3, got {untrusted_auth}"
        )
        assert trusted_auth > untrusted_auth, (
            f"Trusted domain ({trusted_auth}) should have higher source_authority "
            f"than untrusted domain ({untrusted_auth})"
        )

        # The final score should also be higher for trusted domain
        assert trusted_item.final_score > untrusted_item.final_score, (
            f"Trusted domain article ({trusted_item.final_score}) should score higher "
            f"than untrusted domain article ({untrusted_item.final_score})"
        )

    def test_no_trusted_domains_neutral_authority(self, db_session):
        """Without trusted domains configured, all domains get neutral authority."""
        ws = _make_metal_earth_workspace(
            db_session,
            trusted_domains=None,  # No trusted domains configured
        )

        item = _make_item(
            db_session,
            ws.id,
            title="New model kit announced",
            url="https://random-blog.xyz/model-kit",
            content_type="news",
        )

        score_content_items(db_session, [item], ws)

        auth = item.score_breakdown_json["scores"]["source_authority"]
        assert auth == pytest.approx(0.5), (
            f"With no trusted domains, source_authority should be 0.5, got {auth}"
        )


# ---------------------------------------------------------------------------
# Additional integration tests for scoring quality
# ---------------------------------------------------------------------------


class TestMetalEarthScoringPipelineIntegration:
    """End-to-end scoring pipeline tests with realistic Metal Earth scenarios."""

    def test_multiple_articles_ranked_correctly(self, db_session):
        """A corpus of articles should be ranked correctly by relevance."""
        ws = _make_metal_earth_workspace(db_session)

        # Strong article: hits multiple priority themes + trusted domain
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
            url="https://toybook.com/star-wars-model-kits",
        )

        # Medium article: mentions a competitor (competitor_mention is a strong signal)
        medium = _make_item(
            db_session,
            ws.id,
            title="Piececool releases new architecture model kit collection",
            summary_snippet=(
                "Piececool's new architecture model kit collection is now available. "
                "The 3D metal puzzles feature famous landmarks."
            ),
            content_type="news",
            url="https://hobbynews.com/piececool-architecture",
        )

        # Weak article: only tangentially related
        weak = _make_item(
            db_session,
            ws.id,
            title="New DIY craft trend gaining popularity",
            summary_snippet=(
                "DIY crafting continues to grow as a hobby trend. "
                "Many new enthusiasts are joining the community."
            ),
            content_type="news",
            url="https://lifestyle.com/diy-craft-trend",
        )

        # Noise article: completely unrelated
        noise = _make_item(
            db_session,
            ws.id,
            title="Local sports results: football and basketball scores",
            summary_snippet="Weekend sports roundup with all the latest scores.",
            content_type="news",
            url="https://sportsnews.com/weekend-results",
        )

        score_content_items(db_session, [strong, medium, weak, noise], ws)

        # Verify ranking order
        scores = {
            "strong": strong.final_score,
            "medium": medium.final_score,
            "weak": weak.final_score,
            "noise": noise.final_score,
        }

        # All scores should be non-None
        for name, score in scores.items():
            assert score is not None, f"{name} score should not be None"

        # Strong and medium articles (which have theme/competitor signals)
        # should score higher than weak/noise articles
        assert scores["strong"] > scores["noise"], (
            f"Strong ({scores['strong']}) should beat noise ({scores['noise']})"
        )
        assert scores["medium"] > scores["noise"], (
            f"Medium ({scores['medium']}) should beat noise ({scores['noise']})"
        )
        assert scores["strong"] > scores["weak"], (
            f"Strong ({scores['strong']}) should beat weak ({scores['weak']})"
        )

        # At least one of strong/medium should beat weak
        assert max(scores["strong"], scores["medium"]) > scores["weak"], (
            f"At least one of strong ({scores['strong']}) or medium ({scores['medium']}) "
            f"should beat weak ({scores['weak']})"
        )

    def test_score_distribution_not_compressed(self, db_session):
        """Score distribution should have meaningful separation between articles."""
        ws = _make_metal_earth_workspace(db_session)

        # Create a range of articles
        articles = [
            _make_item(
                db_session,
                ws.id,
                title=(
                    "Hasbro and Disney announce new Star Wars licensed franchise "
                    "collectible model kit series"
                ),
                summary_snippet=(
                    "The new Star Wars collectible model kit series from Hasbro and Disney "
                    "brings iconic spacecraft to the toy industry."
                ),
                content_type="news",
            ),
            _make_item(
                db_session,
                ws.id,
                title="New software licensing agreement announced",
                summary_snippet="TechCorp has entered a licensing agreement for enterprise software.",
                content_type="news",
            ),
            _make_item(
                db_session,
                ws.id,
                title="Celebrity gossip roundup",
                summary_snippet="The latest celebrity gossip from Hollywood.",
                content_type="news",
            ),
            _make_item(
                db_session,
                ws.id,
                title="Local weather forecast",
                summary_snippet="Sunny skies expected throughout the weekend.",
                content_type="news",
            ),
        ]

        score_content_items(db_session, articles, ws)

        final_scores = [item.final_score for item in articles]

        # Calculate score range
        max_score = max(final_scores)
        min_score = min(final_scores)
        score_range = max_score - min_score

        # The range should be at least 0.1 to show meaningful separation
        assert score_range >= 0.1, (
            f"Score range ({score_range:.4f}) should be >= 0.1 to show "
            f"meaningful separation between articles"
        )

    def test_excluded_topic_articles_filtered_out(self, db_session):
        """Articles matching excluded topics should be excluded."""
        ws = _make_metal_earth_workspace(db_session)

        # Article matching excluded topic
        crypto_item = _make_item(
            db_session,
            ws.id,
            title="Bitcoin reaches new all-time high as cryptocurrency surges",
            summary_snippet="The cryptocurrency market continues to grow rapidly.",
            content_type="news",
        )

        # Article matching another excluded topic
        gossip_item = _make_item(
            db_session,
            ws.id,
            title="Celebrity gossip: latest drama unfolds",
            summary_snippet="All the celebrity gossip you need to know today.",
            content_type="news",
        )

        # Relevant article
        relevant_item = _make_item(
            db_session,
            ws.id,
            title="New Metal Earth Star Wars model kit announced",
            summary_snippet="A new collectible model kit is coming soon.",
            content_type="news",
        )

        score_content_items(db_session, [crypto_item, gossip_item, relevant_item], ws)

        # Excluded articles should have correct status
        assert crypto_item.status == "excluded"
        assert crypto_item.exclusion_reason == "matched_excluded_topic"
        assert gossip_item.status == "excluded"
        assert gossip_item.exclusion_reason == "matched_excluded_topic"

        # Relevant article should be included
        assert relevant_item.status == "included"

    def test_multi_theme_article_gets_boost(self, db_session):
        """Article matching multiple themes should get multi-signal boost."""
        ws = _make_metal_earth_workspace(db_session)

        # Single theme article
        single_item = _make_item(
            db_session,
            ws.id,
            title="New model kit available",
            summary_snippet="A new model kit is now available for purchase.",
            content_type="news",
        )

        # Multi theme article (matches star wars, model kit, collectibles, etc.)
        multi_item = _make_item(
            db_session,
            ws.id,
            title="New Star Wars collectible model kit combines DIY craft and hobby themes",
            summary_snippet=(
                "A new Star Wars collectible model kit is coming soon for hobbyists. "
                "The metal earth model combines multiple themes."
            ),
            content_type="news",
        )

        score_content_items(db_session, [single_item, multi_item], ws)

        assert multi_item.final_score > single_item.final_score, (
            f"Multi-theme article ({multi_item.final_score}) should score higher "
            f"than single-theme article ({single_item.final_score})"
        )

        # Verify boost appears in breakdown
        breakdown = multi_item.score_breakdown_json
        assert "multi_signal_boost" in breakdown
        assert breakdown["multi_signal_boost"]["bonus"] > 0


# ---------------------------------------------------------------------------
# Regression tests — ensure scoring quality fixes stay in place
# ---------------------------------------------------------------------------


class TestScoringQualityRegression:
    """Regression tests to lock in scoring quality fixes from Passes 1-6."""

    def test_no_semantic_scoring_component_in_breakdown(self, db_session):
        """Score breakdown must NOT contain semantic/LLM scoring components.

        Content scoring is intentionally deterministic/lexical only.
        """
        ws = _make_metal_earth_workspace(db_session)

        item = _make_item(
            db_session,
            ws.id,
            title="Star Wars model kit announced",
            content_type="news",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json

        # These keys must NOT appear
        assert "semantic_relevance" not in breakdown
        assert "semantic_relevance" not in breakdown.get("scores", {})
        assert "llm_score" not in breakdown
        assert "llm_score" not in breakdown.get("scores", {})

    def test_known_scoring_components_only(self, db_session):
        """The score breakdown should only contain known deterministic components."""
        ws = _make_metal_earth_workspace(db_session)

        item = _make_item(
            db_session,
            ws.id,
            title="Star Wars model kit announced",
            content_type="news",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        scores = breakdown.get("scores", {})

        # All known deterministic scoring components
        known_keys = {
            "keyword",
            "competitor_mention",
            "freshness",
            "source_authority",
            "bm25",
            "content_type_prior",
            "feed_health",
        }

        # Any key in scores that is not in known_keys is unexpected
        unknown_keys = set(scores.keys()) - known_keys
        assert unknown_keys == set(), (
            f"Unexpected scoring components found: {unknown_keys}. "
            "Content scoring should only use deterministic/lexical signals."
        )

    def test_competitor_aliases_generated_correctly(self, db_session):
        """Competitor aliases should be generated and exposed in breakdown."""
        # Use a workspace with competitors that have parentheticals
        ws = _make_metal_earth_workspace(
            db_session,
            competitors=[
                "Fascinations (Metal Earth parent company)",
                "Tenyo Metallic Nano (Japanese licensee, same factory)",
            ],
        )

        item = _make_item(
            db_session,
            ws.id,
            title="Tenyo announces new metallic nano model kit",
            content_type="news",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        comp_match = breakdown["competitor_match"]

        # Verify aliases are generated for all competitors
        assert "competitor_aliases" in comp_match
        aliases_dict = comp_match["competitor_aliases"]

        # Check that Fascinations has "metal earth" as an alias (from parenthetical)
        fascinations_key = "fascinations (metal earth parent company)"
        assert fascinations_key in aliases_dict
        assert "metal earth" in aliases_dict[fascinations_key]

        # Check that Tenyo Metallic Nano has expected aliases
        tenyo_key = "tenyo metallic nano (japanese licensee, same factory)"
        assert tenyo_key in aliases_dict
        assert "tenyo" in aliases_dict[tenyo_key]
        assert "metallic nano" in aliases_dict[tenyo_key]

    def test_theme_decomposition_in_breakdown(self, db_session):
        """Decomposed themes should be exposed in the breakdown."""
        ws = _make_metal_earth_workspace(
            db_session,
            priority_themes=[
                "Star Wars, Marvel",
                "licensed merchandise and IP deals",
            ],
        )

        item = _make_item(
            db_session,
            ws.id,
            title="Some article",
            content_type="news",
        )

        score_content_items(db_session, [item], ws)

        breakdown = item.score_breakdown_json
        theme_match = breakdown["theme_match"]

        # Verify decomposed_themes is present
        assert "decomposed_themes" in theme_match
        decomposed = theme_match["decomposed_themes"]

        # "Star Wars, Marvel" should decompose to ["star wars", "marvel"]
        star_wars_key = "star wars, marvel"
        assert star_wars_key in decomposed
        assert "star wars" in decomposed[star_wars_key]
        assert "marvel" in decomposed[star_wars_key]

        # "licensed merchandise and IP deals" should decompose
        licensed_key = "licensed merchandise and ip deals"
        assert licensed_key in decomposed
        assert "licensed merchandise" in decomposed[licensed_key]
        assert "ip deals" in decomposed[licensed_key]
