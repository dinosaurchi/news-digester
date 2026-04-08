"""ProcessingRun API endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.content import ContentItem
from app.models.feed import FeedSource
from app.models.report import Report, ReportMessage
from app.models.run import ProcessingRun, ProcessingRunEvent
from app.schemas.run import _run_summary_to_out, _run_event_to_step
from app.services import run as run_service
from app.services import workspace as ws_service
from app.tasks.pipeline import fetch_feed, generate_report_stub, normalize_content

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
    linked_reports = db.query(Report).filter(Report.run_id == run_id).all()
    out["links"] = {
        "reports": [r.id for r in linked_reports] if linked_reports else None,
        "contentItems": None,
    }

    return out


# ── Run-now trigger ────────────────────────────────────────────────────


@router.post("/workspaces/{workspace_id}/run-now", status_code=201)
def run_now(workspace_id: str, db: Session = Depends(get_db)):
    """Trigger an immediate processing run for a workspace.

    Runs the full pipeline synchronously: fetch feeds → normalize content →
    score content → generate report.  In production this would be dispatched
    to a Celery task and the endpoint would return the run ID immediately.
    """
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # 1. Create the ProcessingRun record
    now = datetime.now(timezone.utc)
    run = ProcessingRun(
        workspace_id=workspace_id,
        run_type="manual",
        status="running",
        started_at=now,
        affected_counts_json={"feeds": 0, "articles": 0, "reports": 0},
    )
    db.add(run)
    db.flush()

    # Preserve started_at locally — SQLite strips tzinfo after commit/expire,
    # which would break the duration calculation below.
    started_at = now

    try:
        # ── Step 1: Fetch feeds ─────────────────────────────────────
        event1 = ProcessingRunEvent(
            run_id=run.id,
            step_name="fetch_feeds",
            status="running",
            message="Fetching feeds...",
        )
        db.add(event1)
        db.commit()

        feeds = (
            db.query(FeedSource)
            .filter(
                FeedSource.workspace_id == workspace_id,
                FeedSource.status != "disabled",
            )
            .all()
        )
        all_items: list[ContentItem] = []
        for feed in feeds:
            raw_items = fetch_feed(feed)
            content_items = normalize_content(workspace_id, feed, raw_items)
            for item in content_items:
                db.add(item)
            all_items.extend(content_items)
            feed.last_fetched_at = datetime.now(timezone.utc)

        event1.status = "success"
        event1.message = f"Fetched {len(feeds)} feeds, found {len(all_items)} articles"

        # ── Step 2: Normalize content ───────────────────────────────
        event2 = ProcessingRunEvent(
            run_id=run.id,
            step_name="normalize_content",
            status="running",
            message="Normalizing content...",
        )
        db.add(event2)
        db.commit()

        event2.status = "success"
        event2.message = f"Normalized {len(all_items)} content items"

        # ── Step 3: Score content (stub) ───────────────────────────
        event3 = ProcessingRunEvent(
            run_id=run.id,
            step_name="score_content",
            status="running",
            message="Scoring content...",
        )
        db.add(event3)
        db.commit()

        # Simple scoring: mark first 5 as included, rest as excluded
        for i, item in enumerate(all_items):
            if i < 5:
                item.status = "included"
                item.final_score = 0.8
                item.inclusion_reason = "High relevance score"
            else:
                item.status = "excluded"
                item.final_score = 0.3
                item.exclusion_reason = "Below relevance threshold"

        included_count = min(5, len(all_items))
        event3.status = "success"
        event3.message = f"Scored {len(all_items)} items, {included_count} included"

        # ── Step 4: Generate report ────────────────────────────────
        event4 = ProcessingRunEvent(
            run_id=run.id,
            step_name="generate_report",
            status="running",
            message="Generating report...",
        )
        db.add(event4)
        db.commit()

        report = generate_report_stub(ws, all_items, run)
        db.add(report)
        db.commit()
        db.refresh(report)

        # Create report thread message
        msg = ReportMessage(
            thread_id=report.id,
            role="system",
            content=report.markdown_body,
            metadata_json={
                "sources": [item.url for item in all_items[:5]],
                "reportId": report.id,
            },
        )
        db.add(msg)
        db.commit()

        event4.status = "success"
        event4.message = f"Generated report: {report.title}"

        # ── Complete run ───────────────────────────────────────────
        finished = datetime.now(timezone.utc)
        run.status = "success"
        run.finished_at = finished
        run.duration_ms = int((finished - started_at).total_seconds() * 1000)
        run.affected_counts_json = {
            "feeds": len(feeds),
            "articles": len(all_items),
            "reports": 1,
        }
        db.commit()
        db.refresh(run)

    except Exception as exc:
        run.status = "failed"
        run.finished_at = datetime.now(timezone.utc)
        run.duration_ms = int((run.finished_at - started_at).total_seconds() * 1000)
        run.error_summary = str(exc)
        db.commit()
        db.refresh(run)

    return _run_summary_to_out(run)
