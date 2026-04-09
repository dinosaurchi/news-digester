"""OpenCode Agent Adapter client layer.

This module is the ONLY place that knows about the opencode adapter.
Pipeline stages call the high-level methods (refine_shortlist, generate_report_markdown);
all HTTP details and error handling are encapsulated here.
"""

from __future__ import annotations

import logging
import json
import re
import time
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
        default_agent: str = "general",
        workspace_dir: str = "/workspace",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._default_model = default_model
        self._enabled = enabled
        self._default_agent = default_agent
        self._workspace_dir = workspace_dir

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

        prompt = self._build_shortlist_prompt(
            input_data=input_data,
            metadata=metadata,
        )
        raw = self._call_adapter_run(
            title="sme-news-shortlist-refinement",
            prompt=prompt,
        )

        output = self._extract_json_object(raw["output_text"])
        selected_items = output.get("selected_items", [])
        rationale = output.get("rationale", "")

        return ShortlistResult(
            selected_items=selected_items,
            rationale=rationale,
            usage=raw.get("usage", {}),
            model=raw.get("model", self._default_model),
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

        prompt = self._build_report_prompt(
            input_data=input_data,
            metadata=metadata,
        )
        raw = self._call_adapter_run(
            title="sme-news-report-generation",
            prompt=prompt,
        )

        markdown = self._extract_report_markdown(raw["output_text"])

        return ReportResult(
            markdown=markdown,
            usage=raw.get("usage", {}),
            model=raw.get("model", self._default_model),
        )

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _call_adapter_run(
        self,
        title: str,
        prompt: str,
    ) -> dict[str, Any]:
        """Create an OpenCode adapter run and return its completed result.

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
            "title": title,
            "model": self._default_model,
            "agent": self._default_agent,
            "workspace_dir": self._workspace_dir,
            "prompt": prompt,
        }

        url = f"{self._base_url}/v1/runs"
        logger.info(
            "OpenCode run request: title=%s model=%s agent=%s url=%s",
            title,
            self._default_model,
            self._default_agent,
            url,
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

        body = self._parse_json_response(response)
        if response.status_code >= 400:
            raise OpenCodeResponseError(self._format_adapter_error(body, response))

        session_id = body.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            raise OpenCodeResponseError(
                "OpenCode adapter /v1/runs response did not include session_id"
            )

        result = self._poll_result(session_id)
        usage = self._fetch_usage(session_id)
        return {
            "output_text": result["output_text"],
            "usage": usage,
            "model": self._default_model,
            "session_id": session_id,
        }

    def _poll_result(self, session_id: str) -> dict[str, Any]:
        """Poll the adapter result endpoint until a run completes or fails."""
        deadline = time.monotonic() + self._timeout
        url = f"{self._base_url}/v1/sessions/{session_id}/result"

        while True:
            if time.monotonic() > deadline:
                raise OpenCodeTimeoutError(
                    f"OpenCode adapter timed out after {self._timeout}s"
                )

            try:
                response = httpx.get(url, timeout=min(10, self._timeout))
            except httpx.ConnectError as exc:
                raise OpenCodeUnavailableError(
                    f"OpenCode adapter is unreachable at {self._base_url}: {exc}"
                ) from exc
            except httpx.TimeoutException:
                time.sleep(1)
                continue

            body = self._parse_json_response(response)
            if response.status_code >= 400:
                raise OpenCodeResponseError(self._format_adapter_error(body, response))

            status = body.get("status")
            if status == "completed":
                output_text = body.get("output_text")
                if not isinstance(output_text, str) or not output_text.strip():
                    raise OpenCodeResponseError(
                        "OpenCode adapter completed without output_text"
                    )
                return {"output_text": output_text}
            if status in {"failed", "aborted"}:
                raise OpenCodeResponseError(
                    f"OpenCode run {session_id} ended with status={status}"
                )

            time.sleep(1)

    def _fetch_usage(self, session_id: str) -> dict[str, Any]:
        """Best-effort usage fetch after a successful run.

        Usage metadata is non-critical; if the endpoint is unavailable or not
        populated, keep the generated content and return an empty dict.
        """
        url = f"{self._base_url}/v1/sessions/{session_id}/usage"
        try:
            response = httpx.get(url, timeout=min(10, self._timeout))
            if response.status_code >= 400:
                return {}
            body = self._parse_json_response(response)
            return body if isinstance(body, dict) else {}
        except (OpenCodeResponseError, httpx.HTTPError):
            logger.info("OpenCode usage metadata unavailable for %s", session_id)
            return {}

    @staticmethod
    def _parse_json_response(response: httpx.Response) -> dict[str, Any]:
        try:
            body = response.json()
        except Exception as exc:
            logger.error("OpenCode adapter returned non-JSON response: %s", exc)
            raise OpenCodeResponseError(
                f"OpenCode adapter returned non-JSON response: {exc}"
            ) from exc

        if not isinstance(body, dict):
            raise OpenCodeResponseError(
                f"OpenCode adapter returned unexpected type: {type(body).__name__}"
            )
        return body

    @staticmethod
    def _format_adapter_error(body: dict[str, Any], response: httpx.Response) -> str:
        raw_error = body.get("error")
        if isinstance(raw_error, dict):
            message = raw_error.get("message") or raw_error.get("code")
            if isinstance(message, str):
                return message
        if isinstance(raw_error, str):
            return raw_error
        return f"OpenCode adapter returned HTTP {response.status_code}"

    @staticmethod
    def _build_shortlist_prompt(
        *,
        input_data: dict[str, Any],
        metadata: dict[str, Any],
    ) -> str:
        return (
            "You are refining an SME news digest shortlist.\n"
            "Return ONLY valid JSON with shape:\n"
            '{"selected_items":[<items copied from input>],"rationale":"<short rationale>"}\n'
            "Keep only items that are highly relevant to the workspace context.\n\n"
            f"INPUT_JSON:\n{json.dumps(input_data, ensure_ascii=False, indent=2)}\n\n"
            f"METADATA_JSON:\n{json.dumps(metadata, ensure_ascii=False, indent=2)}"
        )

    @staticmethod
    def _build_report_prompt(
        *,
        input_data: dict[str, Any],
        metadata: dict[str, Any],
    ) -> str:
        return (
            "You are generating a concise SME news intelligence report.\n"
            "Return ONLY valid JSON with shape:\n"
            '{"markdown":"# <report title>\\n\\n<markdown report body>"}\n'
            "Use markdown. Cite source URLs already present in the input. Do not invent facts.\n\n"
            f"INPUT_JSON:\n{json.dumps(input_data, ensure_ascii=False, indent=2)}\n\n"
            f"METADATA_JSON:\n{json.dumps(metadata, ensure_ascii=False, indent=2)}"
        )

    # ------------------------------------------------------------------
    # Response validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json_object(text: str) -> dict[str, Any]:
        stripped = text.strip()
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
            if match is None:
                raise OpenCodeResponseError(
                    "OpenCode output did not contain a JSON object"
                )
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise OpenCodeResponseError(
                    "OpenCode output did not contain a valid JSON object"
                ) from exc

        if not isinstance(parsed, dict):
            raise OpenCodeResponseError(
                f"Expected JSON object in OpenCode output, got {type(parsed).__name__}"
            )
        return parsed

    @classmethod
    def _extract_report_markdown(cls, text: str) -> str:
        stripped = text.strip()
        try:
            parsed = cls._extract_json_object(stripped)
        except (OpenCodeResponseError, json.JSONDecodeError):
            return stripped

        markdown = parsed.get("markdown")
        if isinstance(markdown, str) and markdown.strip():
            return markdown.strip()
        return stripped
