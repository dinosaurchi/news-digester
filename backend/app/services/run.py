"""ProcessingRun business logic."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.run import ProcessingRun, ProcessingRunEvent
from app.models.report import Report, ReportMessage


def list_runs(
    db: Session,
    workspace_id: str,
    *,
    run_type: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[ProcessingRun]:
    """Return processing runs for a workspace with optional filters, ordered by started_at desc."""
    q = db.query(ProcessingRun).filter(ProcessingRun.workspace_id == workspace_id)

    if run_type is not None:
        q = q.filter(ProcessingRun.run_type == run_type)
    if status is not None:
        q = q.filter(ProcessingRun.status == status)
    if date_from is not None:
        q = q.filter(ProcessingRun.started_at >= date_from)
    if date_to is not None:
        q = q.filter(ProcessingRun.started_at <= date_to)

    q = q.order_by(ProcessingRun.started_at.desc())

    if offset is not None:
        q = q.offset(offset)
    if limit is not None:
        q = q.limit(limit)

    return q.all()


def count_runs(
    db: Session,
    workspace_id: str,
    *,
    run_type: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> int:
    """Return the total count of processing runs matching the given filters."""
    q = db.query(ProcessingRun).filter(ProcessingRun.workspace_id == workspace_id)

    if run_type is not None:
        q = q.filter(ProcessingRun.run_type == run_type)
    if status is not None:
        q = q.filter(ProcessingRun.status == status)
    if date_from is not None:
        q = q.filter(ProcessingRun.started_at >= date_from)
    if date_to is not None:
        q = q.filter(ProcessingRun.started_at <= date_to)

    return q.count()


def has_active_runs(db: Session, workspace_id: str) -> bool:
    """Return True if any runs are currently running or queued for the workspace."""
    return (
        db.query(ProcessingRun)
        .filter(
            ProcessingRun.workspace_id == workspace_id,
            ProcessingRun.status.in_(["running", "queued"]),
        )
        .first()
        is not None
    )


def get_run(db: Session, run_id: str) -> ProcessingRun | None:
    """Return a single processing run by ID, or None."""
    return db.query(ProcessingRun).filter(ProcessingRun.id == run_id).first()


def get_run_events(db: Session, run_id: str) -> list[ProcessingRunEvent]:
    """Return all events for a processing run."""
    return (
        db.query(ProcessingRunEvent)
        .filter(ProcessingRunEvent.run_id == run_id)
        .order_by(ProcessingRunEvent.created_at)
        .all()
    )


def build_log_snippets(events: list[ProcessingRunEvent]) -> list[str]:
    """Extract log snippets from event messages."""
    snippets = []
    for event in events:
        if event.message:
            snippets.append(f"[{event.step_name}] {event.message}")
    return snippets


def get_linked_content_item_ids(db: Session, run_id: str) -> list[str] | None:
    """Return content item IDs referenced by reports generated in the run."""
    reports = db.query(Report).filter(Report.run_id == run_id).all()
    ids: list[str] = []
    seen: set[str] = set()
    for report in reports:
        messages = (
            db.query(ReportMessage)
            .filter(ReportMessage.thread_id == report.id)
            .order_by(ReportMessage.created_at)
            .all()
        )
        for message in messages:
            metadata = message.metadata_json or {}
            for source_id in metadata.get("sources", []):
                if source_id not in seen:
                    ids.append(source_id)
                    seen.add(source_id)
    return ids or None
