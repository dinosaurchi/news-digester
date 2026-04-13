"""Celery tasks and scheduler helpers for the Pass 6 pipeline."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.run import ProcessingRun
from app.models.workspace import Workspace
from app.services import workspace as workspace_service
from app.services.pipeline import execute_workspace_run
from app.services.pipeline_steps import (
    FeedFetchResult,
    fetch_feed,
    normalize_content,
    parse_rfc2822,
)


def get_scheduled_workspace_ids(db: Session) -> list[str]:
    """Return active workspaces with scheduling enabled."""
    from app.models.workspace import WorkspaceSettings

    rows = (
        db.query(Workspace.id)
        .join(WorkspaceSettings, WorkspaceSettings.workspace_id == Workspace.id)
        .filter(Workspace.status == "active")
        .all()
    )
    result: list[str] = []
    for (workspace_id,) in rows:
        settings = workspace_service.get_or_create_settings(db, workspace_id)
        schedule = settings.schedule or {}
        if schedule.get("enabled"):
            result.append(workspace_id)
    return result


@celery_app.task(
    name="app.tasks.pipeline.run_workspace_pipeline",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=30,
    retry_backoff_max=300,
    max_retries=3,
    retry_jitter=True,
)
def run_workspace_pipeline(run_id: str, workspace_id: str) -> dict:
    """Run the pipeline in a worker process for a specific pre-created run.

    The run is expected to already exist with status "queued".  This task
    transitions it to "running", executes the pipeline, and lets
    ``execute_workspace_run`` handle the final "success" / "failed" status.
    """
    db = SessionLocal()
    try:
        run = db.query(ProcessingRun).filter(ProcessingRun.id == run_id).first()
        if run is None:
            raise ValueError(f"Run not found: {run_id}")
        # If a previous attempt already moved the run to a terminal state,
        # return immediately (e.g. after a retry on a now-failed run).
        if run.status in ("success", "failed"):
            return {"runId": run.id, "status": run.status, "skipped": True}

        workspace = workspace_service.get_workspace(db, workspace_id)
        if workspace is None:
            run.status = "failed"
            run.error_summary = f"Workspace not found: {workspace_id}"
            db.commit()
            return {"runId": run.id, "status": "failed"}

        execute_workspace_run(db, workspace, run_type=run.run_type, run=run)
        return {"runId": run.id, "status": run.status}
    finally:
        db.close()


@celery_app.task(name="app.tasks.pipeline.run_scheduled_workspaces")
def run_scheduled_workspaces() -> dict:
    """Beat-triggered scheduler scan for enabled workspaces."""
    db = SessionLocal()
    try:
        workspace_ids = get_scheduled_workspace_ids(db)
    finally:
        db.close()

    enqueued = 0
    for workspace_id in workspace_ids:
        # Create a queued run first, then dispatch the pipeline task.
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            run = ProcessingRun(
                workspace_id=workspace_id,
                run_type="scheduled",
                status="queued",
                started_at=now,
                affected_counts_json={"feeds": 0, "articles": 0, "reports": 0},
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            run_id = run.id
        finally:
            db.close()

        run_workspace_pipeline.delay(run_id, workspace_id)
        enqueued += 1
    return {"enqueued": enqueued, "workspaceIds": workspace_ids}
