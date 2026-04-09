"""OpenCode Agent Adapter client layer.

This module is the ONLY place that knows about the opencode adapter.
Pipeline stages call the high-level methods (refine_shortlist, generate_report_markdown);
all HTTP details and error handling are encapsulated here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class OpenCodeDisabledError(RuntimeError):
    """Raised when OPENCODE_ENABLED=False and an LLM call is attempted."""


class OpenCodeUnavailableError(RuntimeError):
    """Raised when the adapter is unreachable (connection refused)."""


class OpenCodeTimeoutError(RuntimeError):
    """Raised when the adapter request times out."""


class OpenCodeResponseError(RuntimeError):
    """Raised when the adapter returns ok=False or an invalid response."""


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ShortlistResult:
    """Result of a shortlist refinement call."""

    selected_items: list[dict[str, Any]]
    rationale: str
    usage: dict[str, Any] = field(default_factory=dict)
    model: str = ""


@dataclass
class ReportResult:
    """Result of a report generation call."""

    markdown: str
    usage: dict[str, Any] = field(default_factory=dict)
    model: str = ""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class OpenCodeClient:
    """Thin client that talks to the OpenCode Agent Adapter over HTTP."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout: int,
        default_model: str,
        enabled: bool,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._default_model = default_model
        self._enabled = enabled

    # ------------------------------------------------------------------
    # Public API – called by pipeline stages
    # ------------------------------------------------------------------

    def refine_shortlist(
        self,
        items: list[dict[str, Any]],
        workspace_context: dict[str, Any],
    ) -> ShortlistResult:
        """Ask the LLM to refine the candidate shortlist.

        Parameters
        ----------
        items:
            Candidate content items (each a dict with title, url, summary, etc.).
        workspace_context:
            Workspace metadata relevant for relevance scoring.

        Returns
        -------
        ShortlistResult with selected items and rationale.
        """
        input_data: dict[str, Any] = {
            "items": items,
            "workspace_context": workspace_context,
        }
        metadata: dict[str, Any] = {
            "workspace_context": workspace_context,
        }

        raw = self._call_adapter(
            task="shortlist_refinement",
            input_data=input_data,
            metadata=metadata,
        )

        output = self._expect_dict(raw.get("output"))
        selected_items = output.get("selected_items", [])
        rationale = output.get("rationale", "")

        return ShortlistResult(
            selected_items=selected_items,
            rationale=rationale,
            usage=raw.get("usage", {}),
            model=raw.get("model", ""),
        )

    def generate_report_markdown(
        self,
        items: list[dict[str, Any]],
        workspace_context: dict[str, Any],
        period: dict[str, Any],
    ) -> ReportResult:
        """Ask the LLM to generate a report in markdown.

        Parameters
        ----------
        items:
            Shortlisted content items to include in the report.
        workspace_context:
            Workspace metadata relevant for report generation.
        period:
            Dict with ``start`` and ``end`` keys describing the reporting window.

        Returns
        -------
        ReportResult with the generated markdown.
        """
        input_data: dict[str, Any] = {
            "items": items,
            "workspace_context": workspace_context,
            "period": period,
        }
        metadata: dict[str, Any] = {
            "workspace_context": workspace_context,
            "period": period,
        }

        raw = self._call_adapter(
            task="report_generation",
            input_data=input_data,
            metadata=metadata,
        )

        markdown = self._expect_str(raw.get("output"))

        return ReportResult(
            markdown=markdown,
            usage=raw.get("usage", {}),
            model=raw.get("model", ""),
        )

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _call_adapter(
        self,
        task: str,
        input_data: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """POST a request to the adapter and return the parsed response.

        Raises
        ------
        OpenCodeDisabledError
            If ``self._enabled`` is ``False``.
        OpenCodeUnavailableError
            If the adapter is unreachable.
        OpenCodeTimeoutError
            If the request times out.
        OpenCodeResponseError
            If the adapter returns an error or an unexpected payload.
        """
        if not self._enabled:
            raise OpenCodeDisabledError(
                "OpenCode adapter is disabled (OPENCODE_ENABLED=False)"
            )

        payload: dict[str, Any] = {
            "task": task,
            "model": self._default_model,
            "input": input_data,
            "metadata": metadata,
        }

        url = f"{self._base_url}/v1/chat"
        logger.info(
            "OpenCode request: task=%s model=%s url=%s", task, self._default_model, url
        )

        try:
            response = httpx.post(
                url,
                json=payload,
                timeout=self._timeout,
            )
        except httpx.ConnectError as exc:
            logger.error("OpenCode adapter unreachable: %s", exc)
            raise OpenCodeUnavailableError(
                f"OpenCode adapter is unreachable at {self._base_url}: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            logger.error("OpenCode adapter timed out after %ds", self._timeout)
            raise OpenCodeTimeoutError(
                f"OpenCode adapter timed out after {self._timeout}s"
            ) from exc

        # --- Parse response ---
        try:
            body = response.json()
        except Exception as exc:
            logger.error("OpenCode adapter returned non-JSON response: %s", exc)
            raise OpenCodeResponseError(
                f"OpenCode adapter returned non-JSON response: {exc}"
            ) from exc

        logger.info(
            "OpenCode response: status=%s ok=%s",
            response.status_code,
            body.get("ok"),
        )

        if not isinstance(body, dict):
            raise OpenCodeResponseError(
                f"OpenCode adapter returned unexpected type: {type(body).__name__}"
            )

        if body.get("ok") is False:
            error_msg = body.get("error", "Unknown error from adapter")
            logger.error("OpenCode adapter returned error: %s", error_msg)
            raise OpenCodeResponseError(error_msg)

        return body

    # ------------------------------------------------------------------
    # Response validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _expect_dict(value: Any) -> dict[str, Any]:
        """Return *value* if it is a dict, otherwise raise OpenCodeResponseError."""
        if isinstance(value, dict):
            return value
        raise OpenCodeResponseError(
            f"Expected dict in response 'output', got {type(value).__name__}"
        )

    @staticmethod
    def _expect_str(value: Any) -> str:
        """Return *value* if it is a str, otherwise raise OpenCodeResponseError."""
        if isinstance(value, str):
            return value
        raise OpenCodeResponseError(
            f"Expected str in response 'output', got {type(value).__name__}"
        )
