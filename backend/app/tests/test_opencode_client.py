"""Tests for the OpenCodeClient class."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.opencode_client import (
    OpenCodeClient,
    OpenCodeDisabledError,
    OpenCodeResponseError,
    OpenCodeTimeoutError,
    OpenCodeUnavailableError,
    ReportResult,
    ShortlistResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:9001"
DEFAULT_MODEL = "opencode/gpt-5-nano"
TIMEOUT = 30


def _make_client(
    *,
    base_url: str = BASE_URL,
    timeout: int = TIMEOUT,
    default_model: str = DEFAULT_MODEL,
    enabled: bool = True,
) -> OpenCodeClient:
    return OpenCodeClient(
        base_url=base_url,
        timeout=timeout,
        default_model=default_model,
        enabled=enabled,
    )


def _mock_response(json_data: dict) -> MagicMock:
    """Build a fake httpx.Response whose .json() returns *json_data*."""
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.status_code = 200
    return resp


# ---------------------------------------------------------------------------
# 1. Successful refine_shortlist call
# ---------------------------------------------------------------------------


class TestRefineShortlist:
    """OpenCodeClient.refine_shortlist happy path and request shape."""

    @patch("app.services.opencode_client.httpx.post")
    def test_returns_shortlist_result(self, mock_post: MagicMock) -> None:
        """Successful adapter response is unpacked into ShortlistResult."""
        mock_post.return_value = _mock_response(
            {
                "ok": True,
                "output": {
                    "selected_items": [
                        {"title": "Article A", "url": "https://example.com/a"},
                    ],
                    "rationale": "Highly relevant",
                },
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
                "model": DEFAULT_MODEL,
            }
        )

        client = _make_client()
        items = [{"title": "Article A", "url": "https://example.com/a"}]
        ctx = {"customer": "Acme"}

        result = client.refine_shortlist(items, ctx)

        assert isinstance(result, ShortlistResult)
        assert len(result.selected_items) == 1
        assert result.selected_items[0]["title"] == "Article A"
        assert result.rationale == "Highly relevant"
        assert result.usage == {"prompt_tokens": 100, "completion_tokens": 50}
        assert result.model == DEFAULT_MODEL

    @patch("app.services.opencode_client.httpx.post")
    def test_request_shape(self, mock_post: MagicMock) -> None:
        """The POST payload contains the expected keys and structure."""
        mock_post.return_value = _mock_response(
            {
                "ok": True,
                "output": {"selected_items": [], "rationale": "ok"},
                "usage": {},
                "model": DEFAULT_MODEL,
            }
        )

        client = _make_client()
        items = [{"title": "X"}]
        ctx = {"customer": "C"}

        client.refine_shortlist(items, ctx)

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        url = call_kwargs[0][0] if call_kwargs[0] else call_kwargs[1].get("url")
        payload = call_kwargs[1]["json"]

        assert url == f"{BASE_URL}/v1/chat"
        assert payload["task"] == "shortlist_refinement"
        assert payload["model"] == DEFAULT_MODEL
        assert payload["input"]["items"] == items
        assert payload["input"]["workspace_context"] == ctx
        assert payload["metadata"]["workspace_context"] == ctx


# ---------------------------------------------------------------------------
# 2. Successful generate_report_markdown call
# ---------------------------------------------------------------------------


class TestGenerateReportMarkdown:
    """OpenCodeClient.generate_report_markdown happy path and request shape."""

    @patch("app.services.opencode_client.httpx.post")
    def test_returns_report_result(self, mock_post: MagicMock) -> None:
        """Successful adapter response is unpacked into ReportResult."""
        mock_post.return_value = _mock_response(
            {
                "ok": True,
                "output": "# Weekly Report\n\nSummary here.",
                "usage": {"prompt_tokens": 200, "completion_tokens": 300},
                "model": DEFAULT_MODEL,
            }
        )

        client = _make_client()
        items = [{"title": "Article A"}]
        ctx = {"customer": "Acme"}
        period = {"start": "2024-01-01", "end": "2024-01-07"}

        result = client.generate_report_markdown(items, ctx, period)

        assert isinstance(result, ReportResult)
        assert result.markdown == "# Weekly Report\n\nSummary here."
        assert result.usage == {"prompt_tokens": 200, "completion_tokens": 300}
        assert result.model == DEFAULT_MODEL

    @patch("app.services.opencode_client.httpx.post")
    def test_request_shape(self, mock_post: MagicMock) -> None:
        """The POST payload contains task, model, input, metadata."""
        mock_post.return_value = _mock_response(
            {
                "ok": True,
                "output": "# Report",
                "usage": {},
                "model": DEFAULT_MODEL,
            }
        )

        client = _make_client()
        items = [{"title": "A"}]
        ctx = {"customer": "C"}
        period = {"start": "2024-01-01", "end": "2024-01-07"}

        client.generate_report_markdown(items, ctx, period)

        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]

        assert payload["task"] == "report_generation"
        assert payload["model"] == DEFAULT_MODEL
        assert payload["input"]["items"] == items
        assert payload["input"]["workspace_context"] == ctx
        assert payload["input"]["period"] == period
        assert payload["metadata"]["workspace_context"] == ctx
        assert payload["metadata"]["period"] == period


# ---------------------------------------------------------------------------
# 3. OPENCODE_ENABLED=false
# ---------------------------------------------------------------------------


class TestOpenCodeDisabled:
    """When enabled=False, both public methods raise OpenCodeDisabledError."""

    def test_refine_shortlist_raises(self) -> None:
        client = _make_client(enabled=False)
        with pytest.raises(OpenCodeDisabledError, match="disabled"):
            client.refine_shortlist([], {})

    def test_generate_report_markdown_raises(self) -> None:
        client = _make_client(enabled=False)
        with pytest.raises(OpenCodeDisabledError, match="disabled"):
            client.generate_report_markdown([], {}, {})


# ---------------------------------------------------------------------------
# 4. Adapter timeout
# ---------------------------------------------------------------------------


class TestTimeout:
    """httpx.TimeoutException is mapped to OpenCodeTimeoutError."""

    @patch("app.services.opencode_client.httpx.post")
    def test_refine_shortlist_timeout(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = httpx.TimeoutException("timed out")
        client = _make_client()

        with pytest.raises(OpenCodeTimeoutError, match="timed out"):
            client.refine_shortlist([], {})

    @patch("app.services.opencode_client.httpx.post")
    def test_generate_report_markdown_timeout(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = httpx.TimeoutException("timed out")
        client = _make_client()

        with pytest.raises(OpenCodeTimeoutError, match="timed out"):
            client.generate_report_markdown([], {}, {})


# ---------------------------------------------------------------------------
# 5. Adapter unavailable (connection refused)
# ---------------------------------------------------------------------------


class TestUnavailable:
    """httpx.ConnectError is mapped to OpenCodeUnavailableError."""

    @patch("app.services.opencode_client.httpx.post")
    def test_refine_shortlist_connect_error(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        client = _make_client()

        with pytest.raises(OpenCodeUnavailableError, match="unreachable"):
            client.refine_shortlist([], {})

    @patch("app.services.opencode_client.httpx.post")
    def test_generate_report_markdown_connect_error(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        client = _make_client()

        with pytest.raises(OpenCodeUnavailableError, match="unreachable"):
            client.generate_report_markdown([], {}, {})


# ---------------------------------------------------------------------------
# 6. Invalid response (non-JSON)
# ---------------------------------------------------------------------------


class TestInvalidResponse:
    """Non-JSON response from the adapter raises OpenCodeResponseError."""

    @patch("app.services.opencode_client.httpx.post")
    def test_refine_shortlist_non_json(self, mock_post: MagicMock) -> None:
        resp = MagicMock(spec=httpx.Response)
        resp.json.side_effect = ValueError("not json")
        mock_post.return_value = resp

        client = _make_client()
        with pytest.raises(OpenCodeResponseError, match="non-JSON"):
            client.refine_shortlist([], {})

    @patch("app.services.opencode_client.httpx.post")
    def test_generate_report_markdown_non_json(self, mock_post: MagicMock) -> None:
        resp = MagicMock(spec=httpx.Response)
        resp.json.side_effect = ValueError("not json")
        mock_post.return_value = resp

        client = _make_client()
        with pytest.raises(OpenCodeResponseError, match="non-JSON"):
            client.generate_report_markdown([], {}, {})


# ---------------------------------------------------------------------------
# 7. Error response from adapter (ok=false)
# ---------------------------------------------------------------------------


class TestErrorResponse:
    """ok=False in the response body raises OpenCodeResponseError."""

    @patch("app.services.opencode_client.httpx.post")
    def test_refine_shortlist_ok_false(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(
            {"ok": False, "error": "Model not found"}
        )

        client = _make_client()
        with pytest.raises(OpenCodeResponseError, match="Model not found"):
            client.refine_shortlist([], {})

    @patch("app.services.opencode_client.httpx.post")
    def test_generate_report_markdown_ok_false(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(
            {"ok": False, "error": "Model not found"}
        )

        client = _make_client()
        with pytest.raises(OpenCodeResponseError, match="Model not found"):
            client.generate_report_markdown([], {}, {})


# ---------------------------------------------------------------------------
# 8. Configuration-driven model selection
# ---------------------------------------------------------------------------


class TestModelSelection:
    """The default_model is forwarded to the adapter request payload."""

    @patch("app.services.opencode_client.httpx.post")
    def test_custom_model_in_payload(self, mock_post: MagicMock) -> None:
        custom_model = "opencode/claude-4-sonnet"
        mock_post.return_value = _mock_response(
            {
                "ok": True,
                "output": {"selected_items": [], "rationale": "ok"},
                "usage": {},
                "model": custom_model,
            }
        )

        client = _make_client(default_model=custom_model)
        client.refine_shortlist([], {})

        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == custom_model

    @patch("app.services.opencode_client.httpx.post")
    def test_custom_model_in_report_request(self, mock_post: MagicMock) -> None:
        custom_model = "opencode/claude-4-sonnet"
        mock_post.return_value = _mock_response(
            {
                "ok": True,
                "output": "# Report",
                "usage": {},
                "model": custom_model,
            }
        )

        client = _make_client(default_model=custom_model)
        client.generate_report_markdown([], {}, {})

        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == custom_model
