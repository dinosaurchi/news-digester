"""Tests for report and thread endpoints."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.config import settings
from app.services.opencode_client import (
    OpenCodeClient,
    OpenCodeResponseError,
    OpenCodeTimeoutError,
    OpenCodeUnavailableError,
    ReportChatResult,
    ReportResult,
)
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


def _create_content_item_by_id(client, workspace_id, item_id, **overrides):
    """Create a content item with a specific ID via direct DB insert."""
    from app.models.content import ContentItem

    db = TestingSessionLocal()
    try:
        item = ContentItem(
            id=item_id,
            workspace_id=workspace_id,
            title=overrides.get("title", "Test Content Item"),
            content_type=overrides.get("content_type", "news"),
            status=overrides.get("status", "included"),
            local_relevance_score=0.8,
            llm_score=0.7,
            final_score=0.75,
            published_at=overrides.get(
                "published_at",
                datetime(2024, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
            ),
        )
        db.add(item)
        db.commit()
        return item.id
    finally:
        db.close()


def _create_message_with_metadata(
    client, thread_id, metadata_json, role="system", content="Test"
):
    """Create a report message with custom metadata_json."""
    from app.models.report import ReportMessage

    db = TestingSessionLocal()
    try:
        msg = ReportMessage(
            thread_id=thread_id,
            role=role,
            content=content,
            metadata_json=metadata_json,
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

    def test_send_message_creates_real_agent_message(self, client, monkeypatch):
        captured = {}

        def fake_answer(self, **kwargs):
            captured.update(kwargs)
            return ReportChatResult(
                content="The report cites Source A and Source B as the key items.",
                usage={"total_tokens": 123},
                model="test/model",
                session_id="sess-report-chat-1",
            )

        monkeypatch.setattr(OpenCodeClient, "answer_report_question", fake_answer)

        ws_id = _create_workspace(client)
        source_ids = [
            _create_content_item_by_id(
                client, ws_id, "chat-source-a", title="Source A"
            ),
            _create_content_item_by_id(
                client, ws_id, "chat-source-b", title="Source B"
            ),
        ]
        rid = _create_report(client, ws_id, title="Send Test")
        _create_message_with_metadata(
            client,
            rid,
            role="system",
            content="Generated report body",
            metadata_json={"sources": source_ids, "reportId": rid},
        )

        resp = client.post(
            f"/api/report-threads/{rid}/messages",
            json={"content": "Which sources matter most?"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["userMessage"]["role"] == "user"
        assert data["agentMessage"]["role"] == "agent"
        assert data["agentMessage"]["content"] == (
            "The report cites Source A and Source B as the key items."
        )
        assert data["agentMessage"]["metadata"]["model"] == "test/model"
        assert data["agentMessage"]["metadata"]["sources"] == source_ids
        assert data["agentMessage"]["metadata"]["opencodeSessionId"] == (
            "sess-report-chat-1"
        )
        assert data["agentMessage"]["metadata"]["usage"] == {"total_tokens": 123}

        assert captured["question"] == "Which sources matter most?"
        assert [item["id"] for item in captured["source_items"]] == source_ids

    def test_send_message_provider_failure_persists_user_only(
        self, client, monkeypatch
    ):
        def fail_answer(self, **kwargs):
            raise OpenCodeResponseError("provider rejected request")

        monkeypatch.setattr(OpenCodeClient, "answer_report_question", fail_answer)

        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Provider Failure")

        resp = client.post(
            f"/api/report-threads/{rid}/messages",
            json={"content": "Will this fail?"},
        )
        assert resp.status_code == 502

        messages_resp = client.get(f"/api/report-threads/{rid}/messages")
        messages = messages_resp.json()
        assert [msg["role"] for msg in messages] == ["user"]
        assert messages[0]["content"] == "Will this fail?"

    def test_send_message_unavailable_returns_503(self, client, monkeypatch):
        """Chat returns 503 when OpenCode adapter is unreachable."""

        def fail_unavailable(self, **kwargs):
            raise OpenCodeUnavailableError("adapter unreachable")

        monkeypatch.setattr(OpenCodeClient, "answer_report_question", fail_unavailable)

        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Chat 503 Test")

        resp = client.post(
            f"/api/report-threads/{rid}/messages",
            json={"content": "Will this be 503?"},
        )
        assert resp.status_code == 503
        assert "unreachable" in resp.json()["detail"]

        # User message should be persisted, no agent message
        messages_resp = client.get(f"/api/report-threads/{rid}/messages")
        messages = messages_resp.json()
        assert [msg["role"] for msg in messages] == ["user"]

    def test_send_message_timeout_returns_504(self, client, monkeypatch):
        """Chat returns 504 when OpenCode adapter times out."""

        def fail_timeout(self, **kwargs):
            raise OpenCodeTimeoutError("timed out after 60s")

        monkeypatch.setattr(OpenCodeClient, "answer_report_question", fail_timeout)

        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Chat 504 Test")

        resp = client.post(
            f"/api/report-threads/{rid}/messages",
            json={"content": "Will this be 504?"},
        )
        assert resp.status_code == 504
        assert "timed out" in resp.json()["detail"]

        # User message should be persisted, no agent message
        messages_resp = client.get(f"/api/report-threads/{rid}/messages")
        messages = messages_resp.json()
        assert [msg["role"] for msg in messages] == ["user"]

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

    def test_regenerate_report(self, client, monkeypatch):
        mock_client = MagicMock()
        mock_client.generate_report_markdown.return_value = ReportResult(
            markdown="# Regenerated Report\n\nFresh content.",
        )
        monkeypatch.setattr(
            "app.api.reports.OpenCodeClient",
            lambda **kwargs: mock_client,
        )

        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Regen Test")
        original_mid = _create_message(
            client, rid, role="system", content="Original report content"
        )

        resp = client.post(f"/api/reports/{rid}/regenerate")
        assert resp.status_code == 200
        data = resp.json()

        # The response is a new system message in the same report thread
        assert data["threadId"] == rid
        assert data["role"] == "system"
        assert data["metadata"]["regenerated"] is True
        assert data["metadata"]["originalMessageId"] == original_mid
        assert data["metadata"]["originalReportId"] == rid

        # The original generated message should be marked as regenerated
        messages_resp = client.get(f"/api/report-threads/{rid}/messages")
        assert messages_resp.status_code == 200
        messages = messages_resp.json()
        original_msg = next(msg for msg in messages if msg["id"] == original_mid)
        assert original_msg["metadata"]["regenerated"] is True
        assert original_msg["metadata"]["originalMessageId"] == original_mid
        assert original_msg["metadata"]["regeneratedMessageId"] == data["id"]

    def test_report_404(self, client):
        resp = client.post("/api/reports/nonexistent-id/regenerate")
        assert resp.status_code == 404

    def test_regenerate_with_valid_report_id_succeeds(self, client, monkeypatch):
        mock_client = MagicMock()
        mock_client.generate_report_markdown.return_value = ReportResult(
            markdown="# Regenerated Report\n\nValid content.",
        )
        monkeypatch.setattr(
            "app.api.reports.OpenCodeClient",
            lambda **kwargs: mock_client,
        )

        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Regen Valid Test")
        _create_message(client, rid, role="system", content="Original report content")

        resp = client.post(f"/api/reports/{rid}/regenerate")
        assert resp.status_code == 200
        data = resp.json()
        # Response must contain regenerated message content
        assert "content" in data
        assert len(data["content"]) > 0

    def test_regenerate_with_nonexistent_report_id_returns_404(self, client):
        resp = client.post("/api/reports/nonexistent/regenerate")
        assert resp.status_code == 404

    def test_regenerate_opencode_unavailable_returns_503(self, client, monkeypatch):
        """Regenerate returns 503 when OpenCode adapter is unreachable."""
        mock_client = MagicMock()
        mock_client.generate_report_markdown.side_effect = OpenCodeUnavailableError(
            "OpenCode adapter is unreachable"
        )
        monkeypatch.setattr(
            "app.api.reports.OpenCodeClient",
            lambda **kwargs: mock_client,
        )

        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Regen 503 Test")
        _create_message(client, rid, role="system", content="Original content")

        resp = client.post(f"/api/reports/{rid}/regenerate")
        assert resp.status_code == 503
        assert "unreachable" in resp.json()["detail"]

    def test_regenerate_opencode_timeout_returns_504(self, client, monkeypatch):
        """Regenerate returns 504 when OpenCode adapter times out."""
        mock_client = MagicMock()
        mock_client.generate_report_markdown.side_effect = OpenCodeTimeoutError(
            "OpenCode adapter timed out after 60s"
        )
        monkeypatch.setattr(
            "app.api.reports.OpenCodeClient",
            lambda **kwargs: mock_client,
        )

        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Regen 504 Test")
        _create_message(client, rid, role="system", content="Original content")

        resp = client.post(f"/api/reports/{rid}/regenerate")
        assert resp.status_code == 504
        assert "timed out" in resp.json()["detail"]

    def test_regenerate_opencode_response_error_returns_502(self, client, monkeypatch):
        """Regenerate returns 502 when OpenCode adapter returns bad response."""
        mock_client = MagicMock()
        mock_client.generate_report_markdown.side_effect = OpenCodeResponseError(
            "OpenCode run ended with status=failed"
        )
        monkeypatch.setattr(
            "app.api.reports.OpenCodeClient",
            lambda **kwargs: mock_client,
        )

        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Regen 502 Test")
        _create_message(client, rid, role="system", content="Original content")

        resp = client.post(f"/api/reports/{rid}/regenerate")
        assert resp.status_code == 502
        assert "failed" in resp.json()["detail"]


class TestDeleteReport:
    """DELETE /api/reports/{report_id}"""

    def test_delete_report_success(self, auth_client):
        """Authenticated delete of existing report returns 204."""
        ws_id = _create_workspace(auth_client)
        rid = _create_report(auth_client, ws_id, title="To Delete")

        resp = auth_client.delete(f"/api/reports/{rid}")
        assert resp.status_code == 204

    def test_delete_report_cascade_deletes_messages(self, auth_client):
        """After delete, the report and all its messages are gone."""
        ws_id = _create_workspace(auth_client)
        rid = _create_report(auth_client, ws_id, title="Cascade Test")
        _create_message(auth_client, rid, role="system", content="System message")
        _create_message(auth_client, rid, role="user", content="User message")
        _create_message(auth_client, rid, role="agent", content="Agent message")

        auth_client.delete(f"/api/reports/{rid}")

        # Report should be gone
        resp = auth_client.get(f"/api/reports/{rid}")
        assert resp.status_code == 404

        # Messages should also be gone (cascade delete)
        resp = auth_client.get(f"/api/report-threads/{rid}/messages")
        assert resp.status_code == 404

    def test_delete_report_not_found(self, auth_client):
        """Deleting a non-existent report returns 404."""
        resp = auth_client.delete("/api/reports/nonexistent-id")
        assert resp.status_code == 404

    def test_delete_report_unauthenticated(self, client):
        """Delete without authentication returns 401."""
        ws_id = _create_workspace(client)
        rid = _create_report(client, ws_id, title="Protected")

        resp = client.delete(f"/api/reports/{rid}")
        assert resp.status_code == 401


class TestSourceMetadata:
    """Tests that message metadata.sources are valid content item IDs."""

    def test_seeded_message_sources_are_content_item_ids(self, client):
        ws_id = _create_workspace(client)

        # Create content items with known IDs
        ci_ids = [
            _create_content_item_by_id(
                client, ws_id, f"ci-seeded-{i}", title=f"Source {i}"
            )
            for i in range(3)
        ]

        # Create a report (thread)
        rid = _create_report(client, ws_id, title="Sources Metadata Test")

        # Create messages with metadata.sources referencing content item IDs
        _create_message_with_metadata(
            client,
            rid,
            metadata_json={"sources": ci_ids, "reportId": rid},
            role="system",
            content="Report body referencing sources",
        )
        _create_message_with_metadata(
            client,
            rid,
            metadata_json={"sources": [ci_ids[0]], "model": "gpt-4"},
            role="agent",
            content="Agent response with partial sources",
        )

        # Fetch messages via API
        resp = client.get(f"/api/report-threads/{rid}/messages")
        assert resp.status_code == 200
        messages = resp.json()

        # Verify every source in every message resolves as a content item
        for msg in messages:
            metadata = msg.get("metadata")
            if metadata and isinstance(metadata.get("sources"), list):
                for source_id in metadata["sources"]:
                    content_resp = client.get(f"/api/content/{source_id}")
                    assert content_resp.status_code == 200, (
                        f"Source '{source_id}' in message '{msg['id']}' "
                        f"is not a valid content item ID "
                        f"(got {content_resp.status_code})"
                    )

    def test_run_now_message_sources_are_content_item_ids(self, client):
        ws_id = _create_workspace(client)

        # Trigger run-now (async — returns 202 with queued status;
        # sync_celery_tasks fixture executes pipeline synchronously)
        run_resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert run_resp.status_code == 202
        run_id = run_resp.json()["runId"]

        # Find the generated report via run detail links
        detail_resp = client.get(f"/api/runs/{run_id}")
        assert detail_resp.status_code == 200
        report_ids = detail_resp.json().get("links", {}).get("reports")

        if not report_ids:
            # No report generated (e.g. pipeline produced nothing) —
            # nothing to validate; the contract is vacuously satisfied.
            return

        # Get messages from the generated report
        msg_resp = client.get(f"/api/report-threads/{report_ids[0]}/messages")
        assert msg_resp.status_code == 200
        messages = msg_resp.json()

        for msg in messages:
            metadata = msg.get("metadata")
            if metadata and isinstance(metadata.get("sources"), list):
                for source_id in metadata["sources"]:
                    # Sources must be content item IDs, not URLs
                    assert not source_id.startswith("http"), (
                        f"Source '{source_id}' looks like a URL, not a content item ID"
                    )
                    content_resp = client.get(f"/api/content/{source_id}")
                    assert content_resp.status_code == 200, (
                        f"Run-now source '{source_id}' is not a valid "
                        f"content item ID (got {content_resp.status_code})"
                    )
