"""ProcessingRun Pydantic DTOs."""

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class FeedDetail(BaseModel):
    feed_id: str = Field(alias="feedId")
    feed_name: str = Field(alias="feedName")
    feed_url: str = Field(alias="feedUrl")
    status: str
    entries_count: int = Field(alias="entriesCount")
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AffectedCounts(BaseModel):
    feeds: int = 0
    articles: int = 0
    reports: int = 0
    entries_imported: int = Field(default=0, alias="entriesImported")
    entries_skipped: int = Field(default=0, alias="entriesSkipped")
    feeds_succeeded: int = Field(default=0, alias="feedsSucceeded")
    feeds_failed: int = Field(default=0, alias="feedsFailed")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


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


class RunStepMetadata(BaseModel):
    """Metadata attached to a run step event (varies by step type)."""

    feeds_succeeded: Optional[int] = Field(default=None, alias="feedsSucceeded")
    feeds_failed: Optional[int] = Field(default=None, alias="feedsFailed")
    feeds_attempted: Optional[int] = Field(default=None, alias="feedsAttempted")
    entries_fetched: Optional[int] = Field(default=None, alias="entriesFetched")
    entries_imported: Optional[int] = Field(default=None, alias="entriesImported")
    entries_skipped: Optional[int] = Field(default=None, alias="entriesSkipped")
    feed_details: Optional[list[FeedDetail]] = Field(default=None, alias="feedDetails")

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
    metadata: Optional[RunStepMetadata] = None

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
            "entriesImported": affected.get("entries_imported", 0),
            "entriesSkipped": affected.get("entries_skipped", 0),
            "feedsSucceeded": affected.get("feeds_succeeded", 0),
            "feedsFailed": affected.get("feeds_failed", 0),
        },
        "error": run.error_summary,
    }


def _run_event_to_step(event) -> dict:
    """Convert a ProcessingRunEvent ORM object to RunStepOut dict."""
    meta = event.metadata_json or {}
    duration_ms = meta.get("duration_ms") if meta else None
    step: dict = {
        "id": event.id,
        "name": event.step_name,
        "status": event.status,
        "startedAt": meta.get("started_at") if meta else None,
        "completedAt": meta.get("completed_at") if meta else None,
        "durationMs": duration_ms,
        "details": event.message,
        "error": meta.get("error") if meta else None,
    }
    # Expose enriched fetch metadata when present
    if any(
        meta.get(k)
        for k in (
            "feeds_succeeded",
            "feeds_failed",
            "feeds_attempted",
            "entries_fetched",
            "entries_imported",
            "entries_skipped",
            "feed_details",
        )
    ):
        step["metadata"] = {
            "feedsSucceeded": meta.get("feeds_succeeded"),
            "feedsFailed": meta.get("feeds_failed"),
            "feedsAttempted": meta.get("feeds_attempted"),
            "entriesFetched": meta.get("entries_fetched"),
            "entriesImported": meta.get("entries_imported"),
            "entriesSkipped": meta.get("entries_skipped"),
            "feedDetails": meta.get("feed_details"),
        }
    return step
