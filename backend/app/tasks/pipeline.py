"""Celery tasks and scheduler helpers for the Pass 6 pipeline."""

from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.workspace import Workspace
from app.services import workspace as workspace_service
from app.services.pipeline import execute_workspace_run
from app.services.pipeline_steps import (
    fetch_feed,
    generate_report_stub,
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


@celery_app.task(name="app.tasks.pipeline.run_workspace_pipeline")
def run_workspace_pipeline(workspace_id: str, run_type: str = "scheduled") -> dict:
    """Run the current Pass 6 pipeline in a worker process."""
    db = SessionLocal()
    try:
        workspace = workspace_service.get_workspace(db, workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")
        run, items, report = execute_workspace_run(db, workspace, run_type=run_type)
        return {
            "runId": run.id,
            "workspaceId": workspace_id,
            "status": run.status,
            "contentItemCount": len(items),
            "reportId": report.id,
        }
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
        run_workspace_pipeline.delay(workspace_id, run_type="scheduled")
        enqueued += 1
    return {"enqueued": enqueued, "workspaceIds": workspace_ids}
