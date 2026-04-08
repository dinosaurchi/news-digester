"""ProcessingRun API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.run import _run_summary_to_out, _run_event_to_step
from app.services import run as run_service
from app.services import workspace as ws_service

router = APIRouter(prefix="/api", tags=["runs"])


# ── Workspace-scoped run endpoints ────────────────────────────────────


@router.get("/workspaces/{workspace_id}/runs")
def list_runs(
    workspace_id: str,
    type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    dateFrom: str | None = Query(default=None),
    dateTo: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """List processing runs for a workspace with optional filters."""
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Parse date strings
    dt_from = None
    dt_to = None
    if dateFrom:
        try:
            dt_from = datetime.fromisoformat(dateFrom)
        except (ValueError, TypeError):
            raise HTTPException(status_code=422, detail="Invalid dateFrom format")
    if dateTo:
        try:
            dt_to = datetime.fromisoformat(dateTo)
        except (ValueError, TypeError):
            raise HTTPException(status_code=422, detail="Invalid dateTo format")

    runs = run_service.list_runs(
        db,
        workspace_id,
        run_type=type,
        status=status,
        date_from=dt_from,
        date_to=dt_to,
    )
    return [_run_summary_to_out(r) for r in runs]


# ── Run-scoped endpoints ──────────────────────────────────────────────


@router.get("/runs/{run_id}")
def get_run_detail(run_id: str, db: Session = Depends(get_db)):
    """Get a single processing run by ID with detail (steps, logSnippets, links)."""
    run = run_service.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    out = _run_summary_to_out(run)

    # Add steps from events
    events = run_service.get_run_events(db, run_id)
    out["steps"] = [_run_event_to_step(e) for e in events]

    # Add logSnippets
    out["logSnippets"] = run_service.build_log_snippets(events)

    # Add links (reports and content items associated with this run)
    from app.models.report import Report
    from app.models.content import ContentItem

    linked_reports = db.query(Report).filter(Report.run_id == run_id).all()
    out["links"] = {
        "reports": [r.id for r in linked_reports] if linked_reports else None,
        "contentItems": None,
    }

    return out
