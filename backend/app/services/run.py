"""ProcessingRun business logic."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.run import ProcessingRun, ProcessingRunEvent


def list_runs(
    db: Session,
    workspace_id: str,
    *,
    run_type: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
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

    return q.order_by(ProcessingRun.started_at.desc()).all()


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
