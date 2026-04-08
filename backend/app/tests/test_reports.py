"""Tests for report and thread endpoints."""

from app.tests.conftest import TestingSessionLocal


def _create_workspace(client, name="Test WS", customer="Co"):
    resp = client.post("/api/workspaces", json={"name": name, "customer": customer})
    return resp.json()["id"]


def _create_report(client, ws_id, **overrides):
    """Create a report directly via the test DB session."""
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
    """Create a report message directly via the test DB session."""
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


class TestListReports:
    """GET /api/workspaces/{workspace_id}/reports"""

    def test_list_reports_empty(self, client):
        ws_id = _create_workspace(client)
        resp = client.get(f"/api/workspaces/{ws_id}/reports")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_reports_with_data(self, client):
        ws_id = _create_workspace(client)
        rid1 = _create_report(client, ws_id, title="Report A", status="published")
        rid2 = _create_report(client, ws_id, title="Report B", status="draft")

        resp = client.get(f"/api/workspaces/{ws_id}/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        titles = [r["title"] for r in data]
        assert "Report A" in titles
        assert "Report B" in titles
        # Should have camelCase keys
        for r in data:
            assert "workspaceId" in r
            assert "createdAt" in r
            assert "messageCount" in r

    def test_list_reports_workspace_404(self, client):
        resp = client.get("/api/workspaces/nonexistent-id/reports")
        assert resp.status_code == 404


class TestGetReportSummary:
    """GET /api/reports/{report_id}"""

    def test_get_report_summary(self, client):
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Summary Test", status="published")
        _create_message(client, rid, role="system", content="System message")

        resp = client.get(f"/api/reports/{rid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == rid
        assert data["threadId"] == rid
        assert data["title"] == "Summary Test"
        assert data["status"] == "published"
        assert data["messageCount"] == 1

    def test_get_report_summary_not_found(self, client):
        resp = client.get("/api/reports/nonexistent-id")
        assert resp.status_code == 404


class TestGetThreadDetail:
    """GET /api/report-threads/{thread_id}"""

    def test_get_thread_detail(self, client):
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Thread Detail Test")
        _create_message(client, rid, role="agent", content="Agent highlight message")

        resp = client.get(f"/api/report-threads/{rid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == rid
        assert data["title"] == "Thread Detail Test"
        assert data["messageCount"] == 1
        assert data["latestHighlight"] is not None

    def test_get_thread_detail_not_found(self, client):
        resp = client.get("/api/report-threads/nonexistent-id")
        assert resp.status_code == 404


class TestGetThreadMessages:
    """GET /api/report-threads/{thread_id}/messages"""

    def test_get_thread_messages_empty(self, client):
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Empty Thread")

        resp = client.get(f"/api/report-threads/{rid}/messages")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_thread_messages_with_data(self, client):
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Thread With Messages")
        _create_message(client, rid, role="system", content="First")
        _create_message(client, rid, role="user", content="Second")
        _create_message(client, rid, role="agent", content="Third")

        resp = client.get(f"/api/report-threads/{rid}/messages")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert data[0]["role"] == "system"
        assert data[1]["role"] == "user"
        assert data[2]["role"] == "agent"
        # Check camelCase
        assert "threadId" in data[0]
        assert "createdAt" in data[0]

    def test_get_thread_messages_not_found(self, client):
        resp = client.get("/api/report-threads/nonexistent-id/messages")
        assert resp.status_code == 404


class TestSendMessage:
    """POST /api/report-threads/{thread_id}/messages"""

    def test_send_message_creates_user_and_agent(self, client):
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Send Test")

        resp = client.post(
            f"/api/report-threads/{rid}/messages",
            json={"content": "This is my feedback"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "userMessage" in data
        assert "agentMessage" in data
        assert data["userMessage"]["role"] == "user"
        assert data["userMessage"]["content"] == "This is my feedback"
        assert data["agentMessage"]["role"] == "agent"
        assert "Thank you for your feedback" in data["agentMessage"]["content"]

    def test_send_message_thread_not_found(self, client):
        resp = client.post(
            "/api/report-threads/nonexistent-id/messages",
            json={"content": "Hello"},
        )
        assert resp.status_code == 404


class TestThumbMessage:
    """POST /api/report-messages/{message_id}/thumb"""

    def test_thumb_up(self, client):
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Thumb Test")
        mid = _create_message(client, rid, role="agent", content="Great answer")

        resp = client.post(f"/api/report-messages/{mid}/thumb", json={"value": "up"})
        assert resp.status_code == 200
        assert resp.json() == {"success": True}

        # Verify the message now has feedback
        resp = client.get(f"/api/report-threads/{rid}/messages")
        msgs = resp.json()
        agent_msg = [m for m in msgs if m["id"] == mid][0]
        assert agent_msg["feedback"] == "up"

    def test_thumb_toggle_off(self, client):
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Thumb Toggle")
        mid = _create_message(client, rid, role="agent", content="Toggle me")

        # Thumb up
        client.post(f"/api/report-messages/{mid}/thumb", json={"value": "up"})
        # Thumb up again → toggle off
        resp = client.post(f"/api/report-messages/{mid}/thumb", json={"value": "up"})
        assert resp.status_code == 200
        assert resp.json() == {"success": True}

        # Verify feedback is now None
        resp = client.get(f"/api/report-threads/{rid}/messages")
        msgs = resp.json()
        agent_msg = [m for m in msgs if m["id"] == mid][0]
        assert agent_msg["feedback"] is None

    def test_thumb_switch(self, client):
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Thumb Switch")
        mid = _create_message(client, rid, role="agent", content="Switch me")

        # Thumb up
        client.post(f"/api/report-messages/{mid}/thumb", json={"value": "up"})
        # Thumb down → switch
        resp = client.post(f"/api/report-messages/{mid}/thumb", json={"value": "down"})
        assert resp.status_code == 200

        # Verify feedback is now "down"
        resp = client.get(f"/api/report-threads/{rid}/messages")
        msgs = resp.json()
        agent_msg = [m for m in msgs if m["id"] == mid][0]
        assert agent_msg["feedback"] == "down"

    def test_message_404(self, client):
        resp = client.post(
            "/api/report-messages/nonexistent-id/thumb", json={"value": "up"}
        )
        assert resp.status_code == 404


class TestRegenerateReport:
    """POST /api/reports/{report_id}/regenerate"""

    def test_regenerate_report(self, client):
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Regen Test")
        _create_message(client, rid, role="agent", content="Original report content")

        resp = client.post(f"/api/reports/{rid}/regenerate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["metadata"]["regenerated"] is True

    def test_report_404(self, client):
        resp = client.post("/api/reports/nonexistent-id/regenerate")
        assert resp.status_code == 404
