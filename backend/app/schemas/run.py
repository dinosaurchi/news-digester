"""ProcessingRun Pydantic DTOs."""

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class AffectedCounts(BaseModel):
    feeds: int = 0
    articles: int = 0
    reports: int = 0


class RunSummaryOut(BaseModel):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    type: str
    status: str
    started_at: Optional[str] = Field(default=None, alias="startedAt")
    completed_at: Optional[str] = Field(default=None, alias="completedAt")
    duration_ms: Optional[int] = Field(default=None, alias="durationMs")
    affected_counts: AffectedCounts = Field(
        default_factory=AffectedCounts, alias="affectedCounts"
    )
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RunStepOut(BaseModel):
    id: str
    name: str
    status: str
    started_at: Optional[str] = Field(default=None, alias="startedAt")
    completed_at: Optional[str] = Field(default=None, alias="completedAt")
    duration_ms: Optional[int] = Field(default=None, alias="durationMs")
    details: Optional[str] = None
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RunLinks(BaseModel):
    reports: Optional[list[str]] = None
    content_items: Optional[list[str]] = Field(default=None, alias="contentItems")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RunDetailOut(RunSummaryOut):
    steps: list[dict] = Field(default_factory=list, alias="steps")
    log_snippets: list[str] = Field(default_factory=list, alias="logSnippets")
    links: RunLinks = Field(default_factory=RunLinks, alias="links")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


def _run_summary_to_out(run) -> dict:
    """Convert a ProcessingRun ORM object to camelCase dict."""
    affected = run.affected_counts_json or {}
    return {
        "id": run.id,
        "workspaceId": run.workspace_id,
        "type": run.run_type,
        "status": run.status,
        "startedAt": run.started_at.isoformat() if run.started_at else None,
        "completedAt": run.finished_at.isoformat() if run.finished_at else None,
        "durationMs": run.duration_ms,
        "affectedCounts": {
            "feeds": affected.get("feeds", 0),
            "articles": affected.get("articles", 0),
            "reports": affected.get("reports", 0),
        },
        "error": run.error_summary,
    }


def _run_event_to_step(event) -> dict:
    """Convert a ProcessingRunEvent ORM object to RunStepOut dict."""
    meta = event.metadata_json or {}
    duration_ms = meta.get("duration_ms") if meta else None
    return {
        "id": event.id,
        "name": event.step_name,
        "status": event.status,
        "startedAt": meta.get("started_at") if meta else None,
        "completedAt": meta.get("completed_at") if meta else None,
        "durationMs": duration_ms,
        "details": event.message,
        "error": meta.get("error") if meta else None,
    }
