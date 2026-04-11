"""Tests for the OpenCodeClient adapter-run contract."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.opencode_client import (
    OpenCodeClient,
    OpenCodeResponseError,
    OpenCodeTimeoutError,
    OpenCodeUnavailableError,
    ReportResult,
    ReportChatResult,
    ShortlistResult,
)

BASE_URL = "http://localhost:9001"
DEFAULT_MODEL = "opencode/gpt-5-nano"
TIMEOUT = 30


def _make_client(*, timeout: int = TIMEOUT) -> OpenCodeClient:
    return OpenCodeClient(
        base_url=BASE_URL,
        timeout=timeout,
        default_model=DEFAULT_MODEL,
        default_agent="general",
        workspace_dir="/workspace",
    )


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.status_code = status_code
    return resp


def _mock_completed_run(mock_post: MagicMock, mock_get: MagicMock, output_text: str):
    mock_post.return_value = _mock_response(
        {"accepted": True, "session_id": "sess-1"}, status_code=202
    )
    mock_get.side_effect = [
        _mock_response(
            {
                "session_id": "sess-1",
                "status": "completed",
                "output_text": output_text,
            }
        ),
        _mock_response({"session_id": "sess-1", "total_tokens": 123}),
    ]


class TestRefineShortlist:
    """OpenCodeClient.refine_shortlist via POST /v1/runs + GET result."""

    @patch("app.services.opencode_client.httpx.get")
    @patch("app.services.opencode_client.httpx.post")
    def test_returns_shortlist_result(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        _mock_completed_run(
            mock_post,
            mock_get,
            '{"selected_items":[{"title":"Article A"}],"rationale":"Highly relevant"}',
        )

        result = _make_client().refine_shortlist(
            [{"title": "Article A"}], {"customer": "Acme"}
        )

        assert isinstance(result, ShortlistResult)
        assert result.selected_items == [{"title": "Article A"}]
        assert result.rationale == "Highly relevant"
        assert result.usage == {"session_id": "sess-1", "total_tokens": 123}
        assert result.model == DEFAULT_MODEL

    @patch("app.services.opencode_client.httpx.get")
    @patch("app.services.opencode_client.httpx.post")
    def test_request_shape(self, mock_post: MagicMock, mock_get: MagicMock) -> None:
        _mock_completed_run(
            mock_post,
            mock_get,
            '{"selected_items":[],"rationale":"ok"}',
        )

        _make_client().refine_shortlist([{"title": "X"}], {"customer": "C"})

        assert mock_post.call_args[0][0] == f"{BASE_URL}/v1/runs"
        payload = mock_post.call_args[1]["json"]
        assert payload["title"] == "sme-news-shortlist-refinement"
        assert payload["model"] == DEFAULT_MODEL
        assert payload["agent"] == "general"
        assert payload["workspace_dir"] == "/workspace"
        assert "Return ONLY valid JSON" in payload["prompt"]
        assert "shortlist" in payload["prompt"].lower()


class TestGenerateReportMarkdown:
    """OpenCodeClient.generate_report_markdown via adapter runs."""

    @patch("app.services.opencode_client.httpx.get")
    @patch("app.services.opencode_client.httpx.post")
    def test_returns_report_result(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        _mock_completed_run(
            mock_post,
            mock_get,
            '{"markdown":"# Weekly Report\\n\\nSummary here."}',
        )

        result = _make_client().generate_report_markdown(
            [{"title": "Article A"}],
            {"customer": "Acme"},
            {"start": "2024-01-01", "end": "2024-01-07"},
        )

        assert isinstance(result, ReportResult)
        assert result.markdown == "# Weekly Report\n\nSummary here."
        assert result.usage == {"session_id": "sess-1", "total_tokens": 123}

    @patch("app.services.opencode_client.httpx.get")
    @patch("app.services.opencode_client.httpx.post")
    def test_accepts_plain_markdown(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        _mock_completed_run(mock_post, mock_get, "# Report\n\nPlain markdown.")

        result = _make_client().generate_report_markdown([], {}, {})

        assert result.markdown == "# Report\n\nPlain markdown."

    @patch("app.services.opencode_client.httpx.get")
    @patch("app.services.opencode_client.httpx.post")
    def test_strips_code_fences_around_json(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        _mock_completed_run(
            mock_post,
            mock_get,
            '```json\n{"markdown":"# Fenced Report\\n\\nBody."}\n```',
        )

        result = _make_client().generate_report_markdown([], {}, {})

        assert result.markdown == "# Fenced Report\n\nBody."

    @patch("app.services.opencode_client.httpx.get")
    @patch("app.services.opencode_client.httpx.post")
    def test_extracts_markdown_from_json_with_trailing_garbage(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        _mock_completed_run(
            mock_post,
            mock_get,
            '{\n  "markdown": "# Report\\n\\nBody."\n} trailing garbage text',
        )

        result = _make_client().generate_report_markdown([], {}, {})

        assert result.markdown == "# Report\n\nBody."

    @patch("app.services.opencode_client.httpx.get")
    @patch("app.services.opencode_client.httpx.post")
    def test_rejects_json_without_markdown_field(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        _mock_completed_run(
            mock_post,
            mock_get,
            '{"content": "no markdown key here"}',
        )

        with pytest.raises(OpenCodeResponseError, match="markdown"):
            _make_client().generate_report_markdown([], {}, {})


class TestReportChat:
    """OpenCodeClient.answer_report_question via adapter runs."""

    @patch("app.services.opencode_client.httpx.get")
    @patch("app.services.opencode_client.httpx.post")
    def test_returns_report_chat_result(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        _mock_completed_run(mock_post, mock_get, "Answer grounded in Source A.")

        result = _make_client().answer_report_question(
            question="What matters?",
            report_context={"title": "Report", "markdown": "# Report"},
            source_items=[{"id": "ci-1", "title": "Source A"}],
            recent_messages=[{"role": "user", "content": "Previous question"}],
        )

        assert isinstance(result, ReportChatResult)
        assert result.content == "Answer grounded in Source A."
        assert result.usage == {"session_id": "sess-1", "total_tokens": 123}
        assert result.model == DEFAULT_MODEL
        assert result.session_id == "sess-1"

        payload = mock_post.call_args[1]["json"]
        assert payload["title"] == "sme-news-report-chat"
        assert "Use ONLY the report and source_items" in payload["prompt"]
        assert "What matters?" in payload["prompt"]
        assert "Source A" in payload["prompt"]


class TestAdapterFailures:
    @patch("app.services.opencode_client.httpx.post")
    def test_connect_error(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(OpenCodeUnavailableError, match="unreachable"):
            _make_client().refine_shortlist([], {})

    @patch("app.services.opencode_client.httpx.post")
    def test_create_run_timeout(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = httpx.TimeoutException("timed out")

        with pytest.raises(OpenCodeTimeoutError, match="timed out"):
            _make_client().generate_report_markdown([], {}, {})

    @patch("app.services.opencode_client.httpx.get")
    @patch("app.services.opencode_client.httpx.post")
    def test_failed_result_status(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_post.return_value = _mock_response({"session_id": "sess-1"}, 202)
        mock_get.return_value = _mock_response(
            {"session_id": "sess-1", "status": "failed", "output_text": None}
        )

        with pytest.raises(OpenCodeResponseError, match="status=failed"):
            _make_client().refine_shortlist([], {})

    @patch("app.services.opencode_client.httpx.post")
    def test_error_response_from_create_run(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(
            {"error": {"code": "INVALID_MODEL", "message": "Unknown model"}},
            status_code=400,
        )

        with pytest.raises(OpenCodeResponseError, match="Unknown model"):
            _make_client().generate_report_markdown([], {}, {})

    @patch("app.services.opencode_client.httpx.post")
    def test_non_json_response(self, mock_post: MagicMock) -> None:
        resp = MagicMock(spec=httpx.Response)
        resp.json.side_effect = ValueError("not json")
        resp.status_code = 200
        mock_post.return_value = resp

        with pytest.raises(OpenCodeResponseError, match="non-JSON"):
            _make_client().refine_shortlist([], {})


class TestErrorPropagationByMethod:
    """Each public method correctly maps adapter errors to typed exceptions."""

    @patch("app.services.opencode_client.httpx.get")
    @patch("app.services.opencode_client.httpx.post")
    def test_report_chat_connect_error(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        """answer_report_question raises OpenCodeUnavailableError on connect failure."""
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(OpenCodeUnavailableError, match="unreachable"):
            _make_client().answer_report_question(
                question="What?",
                report_context={"title": "Report"},
                source_items=[],
                recent_messages=[],
            )

    @patch("app.services.opencode_client.httpx.get")
    @patch("app.services.opencode_client.httpx.post")
    def test_report_chat_timeout(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        """answer_report_question raises OpenCodeTimeoutError on timeout."""
        mock_post.side_effect = httpx.TimeoutException("timed out")

        with pytest.raises(OpenCodeTimeoutError, match="timed out"):
            _make_client().answer_report_question(
                question="What?",
                report_context={"title": "Report"},
                source_items=[],
                recent_messages=[],
            )

    @patch("app.services.opencode_client.httpx.get")
    @patch("app.services.opencode_client.httpx.post")
    def test_shortlist_timeout(self, mock_post: MagicMock, mock_get: MagicMock) -> None:
        """refine_shortlist raises OpenCodeTimeoutError on timeout."""
        mock_post.side_effect = httpx.TimeoutException("timed out")

        with pytest.raises(OpenCodeTimeoutError, match="timed out"):
            _make_client().refine_shortlist([], {})

    @patch("app.services.opencode_client.httpx.get")
    @patch("app.services.opencode_client.httpx.post")
    def test_report_generation_connect_error(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        """generate_report_markdown raises OpenCodeUnavailableError on connect failure."""
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(OpenCodeUnavailableError, match="unreachable"):
            _make_client().generate_report_markdown([], {}, {})

    @patch("app.services.opencode_client.httpx.get")
    @patch("app.services.opencode_client.httpx.post")
    def test_report_chat_response_error(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        """answer_report_question raises OpenCodeResponseError on bad response."""
        mock_post.return_value = _mock_response(
            {"error": {"code": "RATE_LIMIT", "message": "Too many requests"}},
            status_code=429,
        )

        with pytest.raises(OpenCodeResponseError, match="Too many requests"):
            _make_client().answer_report_question(
                question="What?",
                report_context={"title": "Report"},
                source_items=[],
                recent_messages=[],
            )

    @patch("app.services.opencode_client.httpx.get")
    @patch("app.services.opencode_client.httpx.post")
    def test_poll_result_connect_error(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        """Polling raises OpenCodeUnavailableError if result endpoint is unreachable."""
        mock_post.return_value = _mock_response(
            {"accepted": True, "session_id": "sess-poll-fail"}, status_code=202
        )
        mock_get.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(OpenCodeUnavailableError, match="unreachable"):
            _make_client().refine_shortlist([], {})

    @patch("app.services.opencode_client.httpx.get")
    @patch("app.services.opencode_client.httpx.post")
    def test_poll_result_aborted(
        self, mock_post: MagicMock, mock_get: MagicMock
    ) -> None:
        """Polling raises OpenCodeResponseError if run status is aborted."""
        mock_post.return_value = _mock_response(
            {"accepted": True, "session_id": "sess-abort"}, status_code=202
        )
        mock_get.return_value = _mock_response(
            {"session_id": "sess-abort", "status": "aborted", "output_text": None}
        )

        with pytest.raises(OpenCodeResponseError, match="aborted"):
            _make_client().refine_shortlist([], {})
