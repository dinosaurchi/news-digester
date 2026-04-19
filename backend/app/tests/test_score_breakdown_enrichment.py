"""Tests for score breakdown API enrichment, sentiment labels, and vote toggle fix (Pass 3)."""

from datetime import datetime, timezone

from app.tests.conftest import TestingSessionLocal
from app.services.content import build_score_breakdown
from app.models.content import ContentItem


def _create_workspace(client, name="Test WS", customer="Co"):
    resp = client.post("/api/workspaces", json={"name": name, "customer": customer})
    return resp.json()["id"]


def _create_report(client, ws_id, **overrides):
    from app.models.report import Report

    db = TestingSessionLocal()
    try:
        report = Report(
            workspace_id=ws_id,
            title=overrides.get("title", "Test Report"),
            status=overrides.get("status", "draft"),
            run_id=overrides.get("run_id", "test-run"),
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report.id
    finally:
        db.close()


def _create_message(client, thread_id, role="system", content="Test message"):
    from app.models.report import ReportMessage

    db = TestingSessionLocal()
    try:
        msg = ReportMessage(
            thread_id=thread_id,
            role=role,
            content=content,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg.id
    finally:
        db.close()


def _create_content_item_with_breakdown(
    client, ws_id, score_breakdown_json=None, **overrides
):
    """Create a content item with a specific score_breakdown_json."""
    from app.models.content import ContentItem

    defaults = {
        "workspace_id": ws_id,
        "title": overrides.pop("title", "Test Content Item"),
        "content_type": overrides.pop("content_type", "news"),
        "status": overrides.pop("status", "included"),
        "local_relevance_score": 0.8,
        "llm_score": 0.7,
        "final_score": 0.75,
        "published_at": datetime(2024, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
        "score_breakdown_json": score_breakdown_json,
    }
    defaults.update(overrides)

    db = TestingSessionLocal()
    try:
        item = ContentItem(**defaults)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 1–3: build_score_breakdown enrichment tests
# ---------------------------------------------------------------------------


class TestScoreBreakdownIncludesFeedbackAdjustment:
    """build_score_breakdown exposes feedbackAdjustment when present."""

    def test_score_breakdown_includes_feedback_adjustment(self, client):
        ws_id = _create_workspace(client)
        breakdown_json = {
            "scores": {
                "keyword": 0.5,
                "bm25": 0.3,
                "freshness": 0.9,
                "source_authority": 0.5,
            },
            "feedback_adjustment": 0.1,
            "feedback": {
                "topics_matched": ["AI"],
                "sources_matched": ["TechCrunch"],
                "event_count": 2,
            },
        }
        item = _create_content_item_with_breakdown(
            client, ws_id, score_breakdown_json=breakdown_json
        )

        result = build_score_breakdown(item)
        assert "feedbackAdjustment" in result
        assert result["feedbackAdjustment"] == 0.1


class TestScoreBreakdownIncludesFeedbackDetails:
    """build_score_breakdown exposes feedback details when present."""

    def test_score_breakdown_includes_feedback_details(self, client):
        ws_id = _create_workspace(client)
        breakdown_json = {
            "scores": {
                "keyword": 0.5,
                "bm25": 0.3,
                "freshness": 0.9,
                "source_authority": 0.5,
            },
            "feedback_adjustment": 0.1,
            "feedback": {
                "topics_matched": ["AI", "Cloud"],
                "sources_matched": ["TechCrunch"],
                "event_count": 3,
            },
        }
        item = _create_content_item_with_breakdown(
            client, ws_id, score_breakdown_json=breakdown_json
        )

        result = build_score_breakdown(item)
        assert "feedback" in result
        fb = result["feedback"]
        assert fb["topicsMatched"] == ["AI", "Cloud"]
        assert fb["sourcesMatched"] == ["TechCrunch"]
        assert fb["eventCount"] == 3


class TestScoreBreakdownNoFeedbackWhenNone:
    """build_score_breakdown omits feedbackAdjustment when no feedback data."""

    def test_score_breakdown_no_feedback_when_none(self, client):
        ws_id = _create_workspace(client)
        # No feedback_adjustment or feedback in breakdown
        breakdown_json = {
            "scores": {
                "keyword": 0.5,
                "bm25": 0.3,
                "freshness": 0.9,
                "source_authority": 0.5,
            },
        }
        item = _create_content_item_with_breakdown(
            client, ws_id, score_breakdown_json=breakdown_json
        )

        result = build_score_breakdown(item)
        assert "feedbackAdjustment" not in result
        assert "feedback" not in result


class TestContentDetailApiReturnsFeedbackInBreakdown:
    """GET /api/content/{id} includes feedbackAdjustment in scoreBreakdown."""

    def test_content_detail_api_returns_feedback_in_breakdown(self, client):
        ws_id = _create_workspace(client)
        breakdown_json = {
            "scores": {
                "keyword": 0.5,
                "bm25": 0.3,
                "freshness": 0.9,
                "source_authority": 0.5,
            },
            "feedback_adjustment": 0.15,
            "feedback": {
                "topics_matched": ["AI"],
                "sources_matched": ["TechCrunch"],
                "event_count": 1,
            },
        }
        item = _create_content_item_with_breakdown(
            client, ws_id, score_breakdown_json=breakdown_json
        )

        resp = client.get(f"/api/content/{item.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "scoreBreakdown" in data
        sb = data["scoreBreakdown"]
        assert "feedbackAdjustment" in sb
        assert sb["feedbackAdjustment"] == 0.15
        assert "feedback" in sb
        assert sb["feedback"]["topicsMatched"] == ["AI"]
        assert sb["feedback"]["sourcesMatched"] == ["TechCrunch"]


# ---------------------------------------------------------------------------
# 5–8: Sentiment label tests
# ---------------------------------------------------------------------------


class TestSentimentLabelPositiveWeight:
    """Weight 2.0 → sentiment 'positive'."""

    def test_sentiment_label_positive_weight(self, client):
        ws_id = _create_workspace(client)
        # Create a topic preference with weight 2.0 via the PUT endpoint
        client.put(
            f"/api/workspaces/{ws_id}/preferences/topics",
            json={"preferences": [{"topic": "AI", "weight": 2.0}]},
        )

        resp = client.get(f"/api/workspaces/{ws_id}/feedback/summary")
        assert resp.status_code == 200
        prefs = resp.json()["topicPreferences"]
        assert len(prefs) == 1
        assert prefs[0]["sentiment"] == "positive"


class TestSentimentLabelNegativeWeight:
    """Weight -1.0 → sentiment 'negative'."""

    def test_sentiment_label_negative_weight(self, client):
        ws_id = _create_workspace(client)
        client.put(
            f"/api/workspaces/{ws_id}/preferences/topics",
            json={"preferences": [{"topic": "Clickbait", "weight": -1.0}]},
        )

        resp = client.get(f"/api/workspaces/{ws_id}/feedback/summary")
        assert resp.status_code == 200
        prefs = resp.json()["topicPreferences"]
        assert len(prefs) == 1
        assert prefs[0]["sentiment"] == "negative"


class TestSentimentLabelZeroWeight:
    """Weight 0.0 → sentiment 'neutral'."""

    def test_sentiment_label_zero_weight(self, client):
        ws_id = _create_workspace(client)
        client.put(
            f"/api/workspaces/{ws_id}/preferences/topics",
            json={"preferences": [{"topic": "Neutral", "weight": 0.0}]},
        )

        resp = client.get(f"/api/workspaces/{ws_id}/feedback/summary")
        assert resp.status_code == 200
        prefs = resp.json()["topicPreferences"]
        assert len(prefs) == 1
        assert prefs[0]["sentiment"] == "neutral"


class TestSentimentLabelNeutralWeightOne:
    """Weight 1.0 → sentiment 'positive' (it is a real preference, not neutral)."""

    def test_sentiment_label_neutral_weight_one(self, client):
        ws_id = _create_workspace(client)
        client.put(
            f"/api/workspaces/{ws_id}/preferences/topics",
            json={"preferences": [{"topic": "Cloud", "weight": 1.0}]},
        )

        resp = client.get(f"/api/workspaces/{ws_id}/feedback/summary")
        assert resp.status_code == 200
        prefs = resp.json()["topicPreferences"]
        assert len(prefs) == 1
        assert prefs[0]["sentiment"] == "positive"


# ---------------------------------------------------------------------------
# 9–11: Vote toggle tests
# ---------------------------------------------------------------------------


class TestVoteToggleOffNoEventCreated:
    """Toggling off a vote does not create a new feedback event."""

    def test_vote_toggle_off_no_event_created(self, client):
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Toggle Off Test")
        mid = _create_message(client, rid, role="agent", content="Toggle me")

        from app.models.report import FeedbackEvent

        # Thumb up — creates one event
        client.post(f"/api/report-messages/{mid}/thumb", json={"value": "up"})

        db = TestingSessionLocal()
        try:
            events_after_up = (
                db.query(FeedbackEvent).filter(FeedbackEvent.message_id == mid).all()
            )
            assert len(events_after_up) == 1
        finally:
            db.close()

        # Thumb up again — toggle off, should NOT create a new event
        client.post(f"/api/report-messages/{mid}/thumb", json={"value": "up"})

        db = TestingSessionLocal()
        try:
            events_after_toggle = (
                db.query(FeedbackEvent).filter(FeedbackEvent.message_id == mid).all()
            )
            # Still only 1 event (the original thumbs_up)
            assert len(events_after_toggle) == 1
        finally:
            db.close()


class TestVoteChangeCreatesSingleEvent:
    """Changing vote (up → down) creates 2 events total (one up, one down)."""

    def test_vote_change_creates_single_event(self, client):
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Vote Change Test")
        mid = _create_message(client, rid, role="agent", content="Change me")

        from app.models.report import FeedbackEvent

        # Thumb up
        client.post(f"/api/report-messages/{mid}/thumb", json={"value": "up"})
        # Thumb down — change vote
        client.post(f"/api/report-messages/{mid}/thumb", json={"value": "down"})

        db = TestingSessionLocal()
        try:
            events = (
                db.query(FeedbackEvent).filter(FeedbackEvent.message_id == mid).all()
            )
            # 2 events: one thumbs_up, one thumbs_down
            assert len(events) == 2
            types = {e.feedback_type for e in events}
            assert types == {"thumbs_up", "thumbs_down"}
        finally:
            db.close()


class TestVoteToggleOffClearsMessageFeedback:
    """Toggling off a vote sets report_messages.feedback to None."""

    def test_vote_toggle_off_clears_message_feedback(self, client):
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Clear Feedback Test")
        mid = _create_message(client, rid, role="agent", content="Clear me")

        from app.models.report import ReportMessage

        # Thumb up
        client.post(f"/api/report-messages/{mid}/thumb", json={"value": "up"})

        db = TestingSessionLocal()
        try:
            msg = db.query(ReportMessage).get(mid)
            assert msg.feedback == "up"
        finally:
            db.close()

        # Thumb up again — toggle off
        client.post(f"/api/report-messages/{mid}/thumb", json={"value": "up"})

        db = TestingSessionLocal()
        try:
            msg = db.query(ReportMessage).get(mid)
            assert msg.feedback is None
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Pass 6 — API contract and score-breakdown transparency tests
# ---------------------------------------------------------------------------


class TestContentDetailExposesThemeMatchMetadata:
    """GET /api/content/{id} includes theme_match in scoreBreakdown."""

    def test_content_detail_exposes_theme_match_metadata(self, client):
        ws_id = _create_workspace(client)
        breakdown_json = {
            "scores": {
                "keyword": 0.5,
                "bm25": 0.3,
                "freshness": 0.9,
                "source_authority": 0.5,
            },
            "theme_match": {
                "matched": ["ai", "machine learning"],
                "unmatched": ["blockchain"],
                "normalized_themes": ["ai", "machine learning", "blockchain"],
                "decomposed_themes": {
                    "ai": ["ai"],
                    "machine learning": ["machine learning"],
                    "blockchain": ["blockchain"],
                },
            },
        }
        item = _create_content_item_with_breakdown(
            client, ws_id, score_breakdown_json=breakdown_json
        )

        resp = client.get(f"/api/content/{item.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "scoreBreakdown" in data
        sb = data["scoreBreakdown"]
        assert "themeMatch" in sb
        assert sb["themeMatch"]["matched"] == ["ai", "machine learning"]
        assert sb["themeMatch"]["unmatched"] == ["blockchain"]
        assert "normalized_themes" in sb["themeMatch"]


class TestContentDetailExposesCompetitorMatchMetadata:
    """GET /api/content/{id} includes competitor_match in scoreBreakdown."""

    def test_content_detail_exposes_competitor_match_metadata(self, client):
        ws_id = _create_workspace(client)
        breakdown_json = {
            "scores": {
                "keyword": 0.5,
                "bm25": 0.3,
                "freshness": 0.9,
                "source_authority": 0.5,
            },
            "competitor_match": {
                "matched": ["openai"],
                "unmatched": ["anthropic", "google"],
                "normalized_competitors": ["openai", "anthropic", "google"],
                "competitor_aliases": {
                    "openai": ["openai"],
                    "anthropic": ["anthropic"],
                    "google": ["google"],
                },
            },
        }
        item = _create_content_item_with_breakdown(
            client, ws_id, score_breakdown_json=breakdown_json
        )

        resp = client.get(f"/api/content/{item.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "scoreBreakdown" in data
        sb = data["scoreBreakdown"]
        assert "competitorMatch" in sb
        assert sb["competitorMatch"]["matched"] == ["openai"]
        assert sb["competitorMatch"]["unmatched"] == ["anthropic", "google"]
        assert "normalized_competitors" in sb["competitorMatch"]


class TestContentDetailExposesFilterReasonAndThreshold:
    """GET /api/content/{id} includes filter_reason and threshold in scoreBreakdown."""

    def test_content_detail_exposes_filter_reason_and_threshold(self, client):
        ws_id = _create_workspace(client)
        breakdown_json = {
            "scores": {
                "keyword": 0.3,
                "bm25": 0.2,
                "freshness": 0.9,
                "source_authority": 0.5,
            },
            "filter_reason": "below_relevance_threshold",
            "min_relevance_threshold": 0.15,
        }
        item = _create_content_item_with_breakdown(
            client, ws_id, score_breakdown_json=breakdown_json, status="excluded"
        )

        resp = client.get(f"/api/content/{item.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "scoreBreakdown" in data
        sb = data["scoreBreakdown"]
        assert "filterReason" in sb
        assert sb["filterReason"] == "below_relevance_threshold"
        assert "minRelevanceThreshold" in sb
        assert sb["minRelevanceThreshold"] == 0.15


class TestContentListContractMatchesUpdatedBreakdownFields:
    """Content list response is backward compatible with updated breakdown fields."""

    def test_content_list_contract_matches_updated_breakdown_fields(self, client):
        """Content list should not include scoreBreakdown (only detail endpoint does)."""
        ws_id = _create_workspace(client)
        breakdown_json = {
            "scores": {
                "keyword": 0.5,
                "bm25": 0.3,
                "freshness": 0.9,
                "source_authority": 0.5,
            },
            "theme_match": {
                "matched": ["ai"],
                "unmatched": [],
            },
            "competitor_match": {
                "matched": ["openai"],
                "unmatched": [],
            },
            "multi_signal_boost": {
                "bonus": 0.05,
                "distinct_matched_themes": 2,
            },
        }
        _create_content_item_with_breakdown(
            client, ws_id, score_breakdown_json=breakdown_json
        )

        resp = client.get(f"/api/workspaces/{ws_id}/content")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # List endpoint should NOT include scoreBreakdown
        item = data[0]
        assert "scoreBreakdown" not in item

        # But should still include the basic score fields
        assert "relevanceScore" in item
        assert "bm25Score" in item
        assert "finalScore" in item


class TestContentDetailExposesMultiSignalBoost:
    """GET /api/content/{id} includes multi_signal_boost in scoreBreakdown."""

    def test_content_detail_exposes_multi_signal_boost(self, client):
        ws_id = _create_workspace(client)
        breakdown_json = {
            "scores": {
                "keyword": 0.8,
                "bm25": 0.6,
                "freshness": 0.9,
                "source_authority": 0.7,
            },
            "multi_signal_boost": {
                "bonus": 0.05,
                "distinct_matched_themes": 3,
            },
        }
        item = _create_content_item_with_breakdown(
            client, ws_id, score_breakdown_json=breakdown_json
        )

        resp = client.get(f"/api/content/{item.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "scoreBreakdown" in data
        sb = data["scoreBreakdown"]
        assert "multiSignalBoost" in sb
        assert sb["multiSignalBoost"]["bonus"] == 0.05
        assert sb["multiSignalBoost"]["distinct_matched_themes"] == 3


# ---------------------------------------------------------------------------
# Pass 7 — combinedScore exposure for diagnostic tool
# ---------------------------------------------------------------------------


class TestBuildScoreBreakdownExposesCombinedScore:
    """build_score_breakdown exposes combinedScore when present in raw breakdown."""

    def test_build_score_breakdown_exposes_combined_score(self, client):
        ws_id = _create_workspace(client)
        breakdown_json = {
            "scores": {
                "keyword": 0.5,
                "bm25": 0.3,
                "freshness": 0.9,
                "source_authority": 0.5,
            },
            "weights": {"keyword": 0.25, "bm25": 0.2},
            "combined_score": 0.72,
        }
        item = _create_content_item_with_breakdown(
            client, ws_id, score_breakdown_json=breakdown_json
        )

        result = build_score_breakdown(item)
        assert "combinedScore" in result
        assert result["combinedScore"] == 0.72

    def test_build_score_breakdown_omits_combined_score_when_absent(self, client):
        ws_id = _create_workspace(client)
        breakdown_json = {
            "scores": {
                "keyword": 0.5,
                "bm25": 0.3,
                "freshness": 0.9,
                "source_authority": 0.5,
            },
            "weights": {"keyword": 0.25, "bm25": 0.2},
            # No combined_score key
        }
        item = _create_content_item_with_breakdown(
            client, ws_id, score_breakdown_json=breakdown_json
        )

        result = build_score_breakdown(item)
        assert "combinedScore" not in result

    def test_build_score_breakdown_combined_score_rounded(self, client):
        ws_id = _create_workspace(client)
        breakdown_json = {
            "scores": {
                "keyword": 0.5,
                "bm25": 0.3,
                "freshness": 0.9,
                "source_authority": 0.5,
            },
            "weights": {"keyword": 0.25, "bm25": 0.2},
            "combined_score": 0.723456789,
        }
        item = _create_content_item_with_breakdown(
            client, ws_id, score_breakdown_json=breakdown_json
        )

        result = build_score_breakdown(item)
        assert result["combinedScore"] == 0.7235

    def test_content_detail_api_exposes_combined_score(self, client):
        """GET /api/content/{id} includes combinedScore in scoreBreakdown."""
        ws_id = _create_workspace(client)
        breakdown_json = {
            "scores": {
                "keyword": 0.5,
                "bm25": 0.3,
                "freshness": 0.9,
                "source_authority": 0.5,
            },
            "weights": {"keyword": 0.25, "bm25": 0.2},
            "combined_score": 0.72,
        }
        item = _create_content_item_with_breakdown(
            client, ws_id, score_breakdown_json=breakdown_json
        )

        resp = client.get(f"/api/content/{item.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "scoreBreakdown" in data
        sb = data["scoreBreakdown"]
        assert "combinedScore" in sb
        assert sb["combinedScore"] == 0.72
