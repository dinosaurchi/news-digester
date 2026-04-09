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
