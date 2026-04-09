"""Tests for feedback-aware quality hooks in scoring and report generation.

Covers:
- 7.5.1: Feedback context enrichment to scoring
- 7.5.2: Feedback influence markers in report metadata
- 7.5.3: Unit tests for feedback integration
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.scoring import (
    _compute_feedback_adjustment,
    _load_feedback_signals,
    score_content_items,
)
from app.services.report_generator import _load_feedback_context, generate_report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workspace(db, **overrides):
    """Create a workspace with profile and settings."""
    from app.models.workspace import Workspace, WorkspaceProfile, WorkspaceSettings

    ws = Workspace(
        name=overrides.get("name", "Test"),
        customer=overrides.get("customer", "TestCo"),
    )
    db.add(ws)
    db.flush()

    profile = WorkspaceProfile(
        workspace_id=ws.id,
        priority_themes=overrides.get("priority_themes", ["ai"]),
        competitors=overrides.get("competitors", []),
        excluded_topics=overrides.get("excluded_topics", []),
    )
    db.add(profile)

    thresholds: dict = {
        "min_relevance_score": overrides.get("min_relevance_score", 0.1),
    }
    if "trusted_domains" in overrides:
        thresholds["trusted_domains"] = overrides["trusted_domains"]

    settings = WorkspaceSettings(
        workspace_id=ws.id,
        thresholds=thresholds,
    )
    db.add(settings)
    db.flush()
    return ws


def _make_item(db, ws_id, **overrides):
    """Create a ContentItem with sensible defaults."""
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


def _add_topic_preference(db, ws_id, topic, weight):
    """Add a TopicPreference for the workspace."""
    from app.models.preferences import TopicPreference

    tp = TopicPreference(
        workspace_id=ws_id,
        topic=topic,
        weight=weight,
    )
    db.add(tp)
    db.flush()
    return tp


def _add_source_preference(db, ws_id, source_name, weight):
    """Add a SourcePreference for the workspace."""
    from app.models.preferences import SourcePreference

    sp = SourcePreference(
        workspace_id=ws_id,
        source_name=source_name,
        weight=weight,
    )
    db.add(sp)
    db.flush()
    return sp


def _add_feedback_event(db, ws_id, **overrides):
    """Add a FeedbackEvent for the workspace."""
    from app.models.report import FeedbackEvent

    event = FeedbackEvent(
        workspace_id=ws_id,
        feedback_type=overrides.get("feedback_type", "thumbs_up"),
        value=overrides.get("value"),
        sentiment=overrides.get("sentiment"),
    )
    db.add(event)
    db.flush()
    return event


# ---------------------------------------------------------------------------
# 7.5.1 — Feedback context enrichment to scoring
# ---------------------------------------------------------------------------


class TestFeedbackScoringTopicBoost:
    """Positive topic preference boosts matching item scores."""

    def test_positive_topic_boosts_score(self, db_session):
        ws = _make_workspace(db_session, priority_themes=["ai"])
        _add_topic_preference(db_session, ws.id, "sustainability", weight=2.0)

        # Item matching the preferred topic
        item = _make_item(
            db_session,
            ws.id,
            title="Sustainability trends in green energy",
            summary_snippet="How sustainability is reshaping industries.",
        )

        result_no_fb = score_content_items(
            db_session,
            [item],
            ws,
        )
        score_with_fb = item.final_score
        breakdown = item.score_breakdown_json

        # Feedback should have boosted the score
        assert score_with_fb is not None
        assert "feedback" in breakdown
        assert "feedback_adjustment" in breakdown
        assert breakdown["feedback_adjustment"] > 0
        assert "sustainability" in breakdown["feedback"]["topics_matched"]
        assert (
            breakdown["feedback"]["event_count"] == 0
        )  # no feedback events, just prefs

    def test_negative_topic_suppresses_score(self, db_session):
        ws = _make_workspace(db_session, priority_themes=["ai"])
        _add_topic_preference(db_session, ws.id, "gossip", weight=-2.0)

        item = _make_item(
            db_session,
            ws.id,
            title="Celebrity gossip roundup",
            summary_snippet="The latest celebrity gossip from Hollywood.",
        )

        score_content_items(db_session, [item], ws)
        breakdown = item.score_breakdown_json

        assert "feedback_adjustment" in breakdown
        assert breakdown["feedback_adjustment"] < 0
        assert "gossip" in breakdown["feedback"]["topics_matched"]

    def test_topic_no_match_no_adjustment(self, db_session):
        ws = _make_workspace(db_session, priority_themes=["ai"])
        _add_topic_preference(db_session, ws.id, "blockchain", weight=2.0)

        item = _make_item(
            db_session,
            ws.id,
            title="AI advances in machine learning",
            summary_snippet="New breakthroughs in artificial intelligence.",
        )

        score_content_items(db_session, [item], ws)
        breakdown = item.score_breakdown_json

        # "blockchain" doesn't appear in the text, so no adjustment
        assert "feedback_adjustment" not in breakdown


class TestFeedbackScoringSourceBoost:
    """Source preference influences scoring."""

    def test_positive_source_boosts_score(self, db_session):
        ws = _make_workspace(db_session, priority_themes=["ai"])
        _add_source_preference(db_session, ws.id, "TechCrunch", weight=2.0)

        item = _make_item(
            db_session,
            ws.id,
            title="AI breakthrough announced",
            summary_snippet="A new AI model has been released.",
            source_name="TechCrunch",
        )

        score_content_items(db_session, [item], ws)
        breakdown = item.score_breakdown_json

        assert "feedback_adjustment" in breakdown
        assert breakdown["feedback_adjustment"] > 0
        assert "techcrunch" in breakdown["feedback"]["sources_matched"]

    def test_negative_source_suppresses_score(self, db_session):
        ws = _make_workspace(db_session, priority_themes=["ai"])
        _add_source_preference(db_session, ws.id, "Clickbait Daily", weight=-2.0)

        item = _make_item(
            db_session,
            ws.id,
            title="AI news today",
            summary_snippet="AI is growing.",
            source_name="Clickbait Daily",
        )

        score_content_items(db_session, [item], ws)
        breakdown = item.score_breakdown_json

        assert "feedback_adjustment" in breakdown
        assert breakdown["feedback_adjustment"] < 0
        assert "clickbait daily" in breakdown["feedback"]["sources_matched"]

    def test_source_partial_match(self, db_session):
        """Source preference should match if the key is a substring of the source_name."""
        ws = _make_workspace(db_session, priority_themes=["ai"])
        _add_source_preference(db_session, ws.id, "reuters", weight=1.5)

        item = _make_item(
            db_session,
            ws.id,
            title="AI regulation news",
            summary_snippet="New regulations proposed.",
            source_name="Reuters Tech",
        )

        score_content_items(db_session, [item], ws)
        breakdown = item.score_breakdown_json

        assert "feedback_adjustment" in breakdown
        assert breakdown["feedback_adjustment"] > 0


class TestFeedbackScoringNoData:
    """No feedback data → scores unchanged (no crash)."""

    def test_no_preferences_scores_unchanged(self, db_session):
        ws = _make_workspace(db_session, priority_themes=["ai"])

        item = _make_item(
            db_session,
            ws.id,
            title="AI advances in machine learning",
            summary_snippet="New breakthroughs in artificial intelligence.",
        )

        score_content_items(db_session, [item], ws)
        breakdown = item.score_breakdown_json

        # No feedback data means no feedback adjustment keys
        assert "feedback_adjustment" not in breakdown
        assert "feedback" not in breakdown

    def test_no_preferences_but_feedback_events(self, db_session):
        """Feedback events exist but no preferences → no score adjustment."""
        ws = _make_workspace(db_session, priority_themes=["ai"])
        _add_feedback_event(
            db_session, ws.id, feedback_type="thumbs_up", sentiment="positive"
        )

        item = _make_item(
            db_session,
            ws.id,
            title="AI advances in machine learning",
            summary_snippet="New breakthroughs in artificial intelligence.",
        )

        score_content_items(db_session, [item], ws)
        breakdown = item.score_breakdown_json

        # No preferences, so no adjustment even though events exist
        assert "feedback_adjustment" not in breakdown


class TestFeedbackScoringAdjustmentCapped:
    """Feedback adjustment is capped to prevent large swings."""

    def test_adjustment_never_exceeds_cap(self, db_session):
        ws = _make_workspace(db_session, priority_themes=["ai"])
        # Very high weight — adjustment should still be capped
        _add_topic_preference(db_session, ws.id, "ai", weight=100.0)
        _add_topic_preference(db_session, ws.id, "machine learning", weight=100.0)

        item = _make_item(
            db_session,
            ws.id,
            title="AI and machine learning breakthrough",
            summary_snippet="Advances in AI and machine learning.",
        )

        score_content_items(db_session, [item], ws)
        breakdown = item.score_breakdown_json

        # Adjustment should be capped at ±0.15
        assert abs(breakdown["feedback_adjustment"]) <= 0.15
        # Score should still be in [0, 1]
        assert 0.0 <= item.final_score <= 1.0


# ---------------------------------------------------------------------------
# _compute_feedback_adjustment — pure function tests
# ---------------------------------------------------------------------------


class TestComputeFeedbackAdjustment:
    """Unit tests for the _compute_feedback_adjustment helper."""

    def test_no_weights_no_match(self):
        adj, topics, sources = _compute_feedback_adjustment(
            "AI news today", "TechCrunch", {}, {}
        )
        assert adj == 0.0
        assert topics == []
        assert sources == []

    def test_positive_topic_match(self):
        adj, topics, sources = _compute_feedback_adjustment(
            "sustainability is key", "Source", {"sustainability": 2.0}, {}
        )
        assert adj > 0
        assert "sustainability" in topics
        assert sources == []

    def test_negative_topic_match(self):
        adj, topics, sources = _compute_feedback_adjustment(
            "celebrity gossip today", "Source", {"gossip": -1.5}, {}
        )
        assert adj < 0
        assert "gossip" in topics

    def test_source_match(self):
        adj, topics, sources = _compute_feedback_adjustment(
            "some article", "TechCrunch", {}, {"techcrunch": 2.0}
        )
        assert adj > 0
        assert "techcrunch" in sources

    def test_combined_topic_and_source(self):
        adj, topics, sources = _compute_feedback_adjustment(
            "sustainability report",
            "TechCrunch",
            {"sustainability": 1.0},
            {"techcrunch": 1.0},
        )
        assert adj > 0
        assert "sustainability" in topics
        assert "techcrunch" in sources

    def test_adjustment_is_capped(self):
        """Even extreme weights produce capped adjustments."""
        adj, _, _ = _compute_feedback_adjustment(
            "ai ai ai ai ai", "Source", {"ai": 1000.0}, {}
        )
        assert abs(adj) <= 0.15


# ---------------------------------------------------------------------------
# _load_feedback_signals — DB-based tests
# ---------------------------------------------------------------------------


class TestLoadFeedbackSignals:
    """Tests for _load_feedback_signals database loading."""

    def test_returns_empty_when_no_data(self, db_session):
        ws = _make_workspace(db_session)

        topics, sources, count = _load_feedback_signals(db_session, ws.id)

        assert topics == {}
        assert sources == {}
        assert count == 0

    def test_loads_topic_preferences(self, db_session):
        ws = _make_workspace(db_session)
        _add_topic_preference(db_session, ws.id, "AI", weight=2.0)
        _add_topic_preference(db_session, ws.id, "Cloud", weight=1.5)

        topics, sources, count = _load_feedback_signals(db_session, ws.id)

        assert "ai" in topics
        assert topics["ai"] == 2.0
        assert "cloud" in topics
        assert topics["cloud"] == 1.5
        assert sources == {}

    def test_loads_source_preferences(self, db_session):
        ws = _make_workspace(db_session)
        _add_source_preference(db_session, ws.id, "TechCrunch", weight=2.0)

        topics, sources, count = _load_feedback_signals(db_session, ws.id)

        assert topics == {}
        assert "techcrunch" in sources
        assert sources["techcrunch"] == 2.0

    def test_counts_feedback_events(self, db_session):
        ws = _make_workspace(db_session)
        _add_feedback_event(db_session, ws.id, feedback_type="thumbs_up")
        _add_feedback_event(db_session, ws.id, feedback_type="thumbs_down")

        _, _, count = _load_feedback_signals(db_session, ws.id)

        assert count == 2


# ---------------------------------------------------------------------------
# 7.5.2 — Feedback influence markers in report metadata
# ---------------------------------------------------------------------------


class TestFeedbackReportMetadata:
    """Feedback markers appear in report metadata."""

    def test_no_feedback_no_context_key(self, db_session):
        from app.models.run import ProcessingRun

        ws = _make_workspace(db_session)
        run = ProcessingRun(
            workspace_id=ws.id,
            run_type="manual",
            status="running",
        )
        db_session.add(run)
        db_session.flush()
        item = _make_item(db_session, ws.id, title="AI article")

        report = generate_report(db_session, ws, [item], run)

        assert report.metadata_json is not None
        assert "feedback_context" not in report.metadata_json

    def test_topic_preferences_in_metadata(self, db_session):
        from app.models.run import ProcessingRun

        ws = _make_workspace(db_session)
        _add_topic_preference(db_session, ws.id, "AI", weight=2.0)
        _add_topic_preference(db_session, ws.id, "Gossip", weight=-1.0)

        run = ProcessingRun(
            workspace_id=ws.id,
            run_type="manual",
            status="running",
        )
        db_session.add(run)
        db_session.flush()
        item = _make_item(db_session, ws.id, title="AI article")

        report = generate_report(db_session, ws, [item], run)

        assert report.metadata_json is not None
        fc = report.metadata_json["feedback_context"]
        assert "topics_influenced" in fc
        assert "sources_influenced" in fc
        assert "feedback_event_count" in fc

        topics = fc["topics_influenced"]
        assert len(topics) == 2
        topic_names = [t["topic"] for t in topics]
        assert "AI" in topic_names
        assert "Gossip" in topic_names

        # Check direction markers
        ai_topic = next(t for t in topics if t["topic"] == "AI")
        assert ai_topic["direction"] == "positive"
        gossip_topic = next(t for t in topics if t["topic"] == "Gossip")
        assert gossip_topic["direction"] == "negative"

    def test_source_preferences_in_metadata(self, db_session):
        from app.models.run import ProcessingRun

        ws = _make_workspace(db_session)
        _add_source_preference(db_session, ws.id, "TechCrunch", weight=2.0)

        run = ProcessingRun(
            workspace_id=ws.id,
            run_type="manual",
            status="running",
        )
        db_session.add(run)
        db_session.flush()
        item = _make_item(db_session, ws.id, title="AI article")

        report = generate_report(db_session, ws, [item], run)

        fc = report.metadata_json["feedback_context"]
        sources = fc["sources_influenced"]
        assert len(sources) == 1
        assert sources[0]["source"] == "TechCrunch"
        assert sources[0]["direction"] == "positive"

    def test_feedback_event_count_in_metadata(self, db_session):
        from app.models.run import ProcessingRun

        ws = _make_workspace(db_session)
        _add_topic_preference(db_session, ws.id, "AI", weight=1.0)
        _add_feedback_event(db_session, ws.id, feedback_type="thumbs_up")
        _add_feedback_event(db_session, ws.id, feedback_type="thumbs_down")

        run = ProcessingRun(
            workspace_id=ws.id,
            run_type="manual",
            status="running",
        )
        db_session.add(run)
        db_session.flush()
        item = _make_item(db_session, ws.id, title="AI article")

        report = generate_report(db_session, ws, [item], run)

        fc = report.metadata_json["feedback_context"]
        assert fc["feedback_event_count"] == 2

    def test_sources_still_present_with_feedback(self, db_session):
        from app.models.run import ProcessingRun

        ws = _make_workspace(db_session)
        _add_topic_preference(db_session, ws.id, "AI", weight=1.0)

        run = ProcessingRun(
            workspace_id=ws.id,
            run_type="manual",
            status="running",
        )
        db_session.add(run)
        db_session.flush()
        item = _make_item(db_session, ws.id, title="AI article")

        report = generate_report(db_session, ws, [item], run)

        # Original "sources" key still present
        assert "sources" in report.metadata_json
        assert item.id in report.metadata_json["sources"]
        # And feedback_context is added
        assert "feedback_context" in report.metadata_json


# ---------------------------------------------------------------------------
# _load_feedback_context — unit tests
# ---------------------------------------------------------------------------


class TestLoadFeedbackContext:
    """Tests for _load_feedback_context helper."""

    def test_returns_none_when_no_data(self, db_session):
        ws = _make_workspace(db_session)

        result = _load_feedback_context(db_session, ws.id)

        assert result is None

    def test_returns_context_with_topic_prefs(self, db_session):
        ws = _make_workspace(db_session)
        _add_topic_preference(db_session, ws.id, "AI", weight=1.0)

        result = _load_feedback_context(db_session, ws.id)

        assert result is not None
        assert len(result["topics_influenced"]) == 1
        assert result["topics_influenced"][0]["topic"] == "AI"
        assert result["sources_influenced"] == []
        assert result["feedback_event_count"] == 0

    def test_returns_context_with_events_only(self, db_session):
        ws = _make_workspace(db_session)
        _add_feedback_event(db_session, ws.id, feedback_type="thumbs_up")

        result = _load_feedback_context(db_session, ws.id)

        assert result is not None
        assert result["topics_influenced"] == []
        assert result["sources_influenced"] == []
        assert result["feedback_event_count"] == 1
