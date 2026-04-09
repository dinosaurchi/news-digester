"""Feedback API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.report import FeedbackCreateIn, _feedback_event_to_out
from app.services import feedback as feedback_service
from app.services import workspace as ws_service
from app.services import report as report_service
from app.models.report import Report, ReportMessage

router = APIRouter(prefix="/api", tags=["feedback"])


@router.get("/workspaces/{workspace_id}/feedback")
def list_feedback(workspace_id: str, db: Session = Depends(get_db)):
    """List all feedback events for a workspace."""
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    events = feedback_service.list_feedback_events(db, workspace_id)
    result = []
    for event in events:
        # Enrich with report title and message excerpt if available
        report_title = None
        message_excerpt = None
        if event.thread_id:
            report = report_service.get_report(db, event.thread_id)
            if report:
                report_title = report.title
        if event.message_id:
            msg = report_service.get_message(db, event.message_id)
            if msg and msg.content:
                message_excerpt = (
                    msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
                )
        result.append(
            _feedback_event_to_out(
                event, report_title=report_title, message_excerpt=message_excerpt
            )
        )
    return result


@router.get("/workspaces/{workspace_id}/feedback/summary")
def get_feedback_summary(workspace_id: str, db: Session = Depends(get_db)):
    """Get a computed feedback summary for a workspace."""
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    return feedback_service.get_feedback_summary(db, workspace_id)


@router.post("/workspaces/{workspace_id}/feedback", status_code=201)
def create_feedback(
    workspace_id: str, body: FeedbackCreateIn, db: Session = Depends(get_db)
):
    """Create a new feedback event."""
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    event = feedback_service.create_feedback_event(
        db,
        workspace_id=workspace_id,
        feedback_type=body.type,
        value=body.value,
        sentiment=body.sentiment,
        thread_id=body.threadId,
        message_id=body.messageId,
    )
    db.commit()
    db.refresh(event)

    # Enrich with report title and message excerpt
    report_title = None
    message_excerpt = None
    if event.thread_id:
        report = report_service.get_report(db, event.thread_id)
        if report:
            report_title = report.title
    if event.message_id:
        msg = report_service.get_message(db, event.message_id)
        if msg and msg.content:
            message_excerpt = (
                msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
            )

    return _feedback_event_to_out(
        event, report_title=report_title, message_excerpt=message_excerpt
    )
