"""Tests for feedback endpoints."""

from app.tests.conftest import TestingSessionLocal


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


def _create_feedback_event(client, ws_id, **overrides):
    from app.models.report import FeedbackEvent

    db = TestingSessionLocal()
    try:
        event = FeedbackEvent(
            workspace_id=ws_id,
            feedback_type=overrides.get("feedback_type", "thumbs_up"),
            value=overrides.get("value"),
            sentiment=overrides.get("sentiment"),
            thread_id=overrides.get("thread_id"),
            message_id=overrides.get("message_id"),
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event.id
    finally:
        db.close()


class TestListFeedback:
    """GET /api/workspaces/{workspace_id}/feedback"""

    def test_list_feedback_empty(self, client):
        ws_id = _create_workspace(client)
        resp = client.get(f"/api/workspaces/{ws_id}/feedback")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_feedback_with_data(self, client):
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Feedback Report")
        _create_feedback_event(
            client,
            ws_id,
            feedback_type="thumbs_up",
            sentiment="positive",
            thread_id=rid,
        )
        _create_feedback_event(
            client,
            ws_id,
            feedback_type="thumbs_down",
            sentiment="negative",
            thread_id=rid,
        )

        resp = client.get(f"/api/workspaces/{ws_id}/feedback")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        types = [e["type"] for e in data]
        assert "thumbs_up" in types
        assert "thumbs_down" in types
        # Check camelCase keys
        for e in data:
            assert "workspaceId" in e
            assert "createdAt" in e

    def test_feedback_workspace_404(self, client):
        resp = client.get("/api/workspaces/nonexistent-id/feedback")
        assert resp.status_code == 404


class TestGetFeedbackSummary:
    """GET /api/workspaces/{workspace_id}/feedback/summary"""

    def test_get_feedback_summary_empty(self, client):
        ws_id = _create_workspace(client)
        resp = client.get(f"/api/workspaces/{ws_id}/feedback/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["totalEvents"] == 0
        assert data["thumbsUp"] == 0
        assert data["thumbsDown"] == 0
        assert data["netSentiment"] == 0
        assert data["topicPreferences"] == []
        assert data["sourcePreferences"] == []
        assert data["reportStylePreferences"] == []

    def test_get_feedback_summary_with_data(self, client):
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Summary Report")
        # Create various feedback events
        _create_feedback_event(
            client, ws_id, feedback_type="thumbs_up", sentiment="positive"
        )
        _create_feedback_event(
            client, ws_id, feedback_type="thumbs_up", sentiment="positive"
        )
        _create_feedback_event(
            client, ws_id, feedback_type="thumbs_down", sentiment="negative"
        )
        _create_feedback_event(
            client,
            ws_id,
            feedback_type="topic_preference",
            value="Generative AI",
            sentiment="positive",
        )
        _create_feedback_event(
            client,
            ws_id,
            feedback_type="topic_preference",
            value="Cybersecurity",
            sentiment="positive",
        )
        _create_feedback_event(
            client,
            ws_id,
            feedback_type="source_preference",
            value="TechCrunch",
            sentiment="positive",
        )
        _create_feedback_event(
            client,
            ws_id,
            feedback_type="comment",
            value="Good report overall",
        )

        resp = client.get(f"/api/workspaces/{ws_id}/feedback/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["totalEvents"] == 7
        assert data["thumbsUp"] == 2
        assert data["thumbsDown"] == 1
        assert data["netSentiment"] == 1
        assert len(data["topicPreferences"]) == 2
        assert len(data["sourcePreferences"]) == 1
        assert data["sourcePreferences"][0]["source"] == "TechCrunch"
        assert data["reportStylePreferences"] == []

    def test_feedback_summary_workspace_404(self, client):
        resp = client.get("/api/workspaces/nonexistent-id/feedback/summary")
        assert resp.status_code == 404


class TestCreateFeedback:
    """POST /api/workspaces/{workspace_id}/feedback"""

    def test_create_feedback_event(self, client):
        ws_id = _create_workspace(client)

        resp = client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={
                "type": "thumbs_up",
                "sentiment": "positive",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "thumbs_up"
        assert data["sentiment"] == "positive"
        assert data["workspaceId"] == ws_id
        assert "id" in data
        assert "createdAt" in data

    def test_create_feedback_with_thread(self, client):
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Thread Report")

        resp = client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={
                "type": "topic_preference",
                "value": "AI Regulation",
                "sentiment": "positive",
                "threadId": rid,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "topic_preference"
        assert data["value"] == "AI Regulation"
        assert data["threadId"] == rid
        assert data["reportTitle"] == "Thread Report"

    def test_create_feedback_validation(self, client):
        ws_id = _create_workspace(client)

        # Invalid type
        resp = client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={
                "type": "invalid_type",
            },
        )
        assert resp.status_code == 422

    def test_create_feedback_workspace_404(self, client):
        resp = client.post(
            "/api/workspaces/nonexistent-id/feedback",
            json={"type": "thumbs_up"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 7.5.4 — Integration tests for feedback continuity
# ---------------------------------------------------------------------------


class TestFeedbackThumbsUpDownContinuity:
    """Thumbs up/down still persist and read back correctly after feedback hooks."""

    def test_thumbs_up_persists_and_reads_back(self, client):
        ws_id = _create_workspace(client)

        # Create thumbs up
        resp = client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={"type": "thumbs_up", "sentiment": "positive"},
        )
        assert resp.status_code == 201
        event_id = resp.json()["id"]

        # Read back via list
        resp = client.get(f"/api/workspaces/{ws_id}/feedback")
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) == 1
        assert events[0]["id"] == event_id
        assert events[0]["type"] == "thumbs_up"
        assert events[0]["sentiment"] == "positive"

    def test_thumbs_down_persists_and_reads_back(self, client):
        ws_id = _create_workspace(client)

        # Create thumbs down
        resp = client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={"type": "thumbs_down", "sentiment": "negative"},
        )
        assert resp.status_code == 201
        event_id = resp.json()["id"]

        # Read back
        resp = client.get(f"/api/workspaces/{ws_id}/feedback")
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) == 1
        assert events[0]["id"] == event_id
        assert events[0]["type"] == "thumbs_down"
        assert events[0]["sentiment"] == "negative"

    def test_multiple_thumbs_persist_correctly(self, client):
        ws_id = _create_workspace(client)

        # Create several thumbs events
        for _ in range(3):
            client.post(
                f"/api/workspaces/{ws_id}/feedback",
                json={"type": "thumbs_up", "sentiment": "positive"},
            )
        for _ in range(2):
            client.post(
                f"/api/workspaces/{ws_id}/feedback",
                json={"type": "thumbs_down", "sentiment": "negative"},
            )

        # Read back
        resp = client.get(f"/api/workspaces/{ws_id}/feedback")
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) == 5
        up_count = sum(1 for e in events if e["type"] == "thumbs_up")
        down_count = sum(1 for e in events if e["type"] == "thumbs_down")
        assert up_count == 3
        assert down_count == 2

    def test_thumbs_up_down_reflected_in_summary(self, client):
        ws_id = _create_workspace(client)

        client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={"type": "thumbs_up", "sentiment": "positive"},
        )
        client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={"type": "thumbs_up", "sentiment": "positive"},
        )
        client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={"type": "thumbs_down", "sentiment": "negative"},
        )

        resp = client.get(f"/api/workspaces/{ws_id}/feedback/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["thumbsUp"] == 2
        assert data["thumbsDown"] == 1
        assert data["netSentiment"] == 1


class TestFeedbackChatboxContinuity:
    """Chatbox feedback (messages) still creates messages correctly."""

    def test_feedback_with_message_reference(self, client):
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Chatbox Report")
        mid = _create_message(client, rid, role="user", content="User question")

        # Create feedback linked to a message
        resp = client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={
                "type": "thumbs_up",
                "sentiment": "positive",
                "threadId": rid,
                "messageId": mid,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["threadId"] == rid
        assert data["messageId"] == mid

    def test_feedback_enriches_with_message_excerpt(self, client):
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Excerpt Report")
        long_content = "This is a very long message that should be truncated to 80 characters in the excerpt"
        mid = _create_message(client, rid, role="user", content=long_content)

        resp = client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={
                "type": "thumbs_up",
                "sentiment": "positive",
                "threadId": rid,
                "messageId": mid,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "messageExcerpt" in data
        assert len(data["messageExcerpt"]) <= 83  # 80 chars + "..."
        assert "This is a very long message" in data["messageExcerpt"]

    def test_feedback_without_message_still_works(self, client):
        ws_id = _create_workspace(client)

        resp = client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={"type": "comment", "value": "Good report"},
        )
        assert resp.status_code == 201
        data = resp.json()
        # No thread or message → no enrichment fields
        assert data.get("reportTitle") is None
        assert data.get("messageExcerpt") is None


class TestFeedbackQueryabilityContinuity:
    """Feedback events are still queryable via API after feedback hooks."""

    def test_all_feedback_types_queryable(self, client):
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Query Report")

        # Create events of various types
        types_to_create = [
            {"type": "thumbs_up", "sentiment": "positive"},
            {"type": "thumbs_down", "sentiment": "negative"},
            {
                "type": "topic_preference",
                "value": "AI",
                "sentiment": "positive",
                "threadId": rid,
            },
            {
                "type": "source_preference",
                "value": "TechCrunch",
                "sentiment": "positive",
            },
            {"type": "comment", "value": "Nice work"},
        ]

        for body in types_to_create:
            resp = client.post(f"/api/workspaces/{ws_id}/feedback", json=body)
            assert resp.status_code == 201, f"Failed for type {body['type']}"

        # Query all events
        resp = client.get(f"/api/workspaces/{ws_id}/feedback")
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) == 5
        event_types = {e["type"] for e in events}
        assert event_types == {
            "thumbs_up",
            "thumbs_down",
            "topic_preference",
            "source_preference",
            "comment",
        }

    def test_feedback_summary_counts_all_types(self, client):
        ws_id = _create_workspace(client)

        client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={"type": "thumbs_up", "sentiment": "positive"},
        )
        client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={"type": "thumbs_down", "sentiment": "negative"},
        )
        client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={"type": "topic_preference", "value": "AI", "sentiment": "positive"},
        )
        client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={
                "type": "source_preference",
                "value": "Reuters",
                "sentiment": "positive",
            },
        )

        resp = client.get(f"/api/workspaces/{ws_id}/feedback/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["totalEvents"] == 4
        assert data["thumbsUp"] == 1
        assert data["thumbsDown"] == 1
        assert len(data["topicPreferences"]) == 1
        assert len(data["sourcePreferences"]) == 1

    def test_feedback_isolated_by_workspace(self, client):
        ws_a = _create_workspace(client, name="WS-A", customer="CoA")
        ws_b = _create_workspace(client, name="WS-B", customer="CoB")

        # Create events for WS-A only
        client.post(
            f"/api/workspaces/{ws_a}/feedback",
            json={"type": "thumbs_up", "sentiment": "positive"},
        )

        # WS-A should have events
        resp_a = client.get(f"/api/workspaces/{ws_a}/feedback")
        assert resp_a.status_code == 200
        assert len(resp_a.json()) == 1

        # WS-B should have no events
        resp_b = client.get(f"/api/workspaces/{ws_b}/feedback")
        assert resp_b.status_code == 200
        assert len(resp_b.json()) == 0


class TestFeedbackEndpointsNoRegression:
    """Ensure no regressions in existing feedback endpoint shapes and behavior."""

    def test_create_response_shape_unchanged(self, client):
        ws_id = _create_workspace(client)

        resp = client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={"type": "thumbs_up", "sentiment": "positive"},
        )
        assert resp.status_code == 201
        data = resp.json()
        # Verify expected camelCase keys exist (DTO shape must not change)
        expected_keys = {"id", "type", "sentiment", "workspaceId", "createdAt"}
        for key in expected_keys:
            assert key in data, f"Missing key '{key}' in create response"

    def test_list_response_shape_unchanged(self, client):
        ws_id = _create_workspace(client)
        _create_feedback_event(
            client, ws_id, feedback_type="thumbs_up", sentiment="positive"
        )

        resp = client.get(f"/api/workspaces/{ws_id}/feedback")
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) == 1
        expected_keys = {"id", "type", "sentiment", "workspaceId", "createdAt"}
        for key in expected_keys:
            assert key in events[0], f"Missing key '{key}' in list response"

    def test_summary_response_shape_unchanged(self, client):
        ws_id = _create_workspace(client)

        resp = client.get(f"/api/workspaces/{ws_id}/feedback/summary")
        assert resp.status_code == 200
        data = resp.json()
        expected_keys = {
            "totalEvents",
            "thumbsUp",
            "thumbsDown",
            "netSentiment",
            "topicPreferences",
            "sourcePreferences",
            "reportStylePreferences",
        }
        for key in expected_keys:
            assert key in data, f"Missing key '{key}' in summary response"

    def test_workspace_not_found_returns_404(self, client):
        endpoints = [
            "/api/workspaces/nonexistent-id/feedback",
            "/api/workspaces/nonexistent-id/feedback/summary",
        ]
        for url in endpoints:
            resp = client.get(url)
            assert resp.status_code == 404, f"Expected 404 for {url}"

    def test_invalid_feedback_type_returns_422(self, client):
        ws_id = _create_workspace(client)

        resp = client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={"type": "totally_invalid_type"},
        )
        assert resp.status_code == 422
