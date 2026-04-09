"""Reports API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.models.content import ContentItem
from app.models.run import ProcessingRun
from app.schemas.report import (
    MessageSendIn,
    ThumbIn,
    _report_to_thread_out,
    _report_to_summary_out,
    _message_to_out,
)
from app.services import report as report_service
from app.services import feedback as feedback_service
from app.services import workspace as ws_service
from app.services.opencode_client import OpenCodeClient
from app.services.report_generator import generate_report

router = APIRouter(prefix="/api", tags=["reports"])


# ── Workspace-scoped report endpoints ────────────────────────────────


@router.get("/workspaces/{workspace_id}/reports")
def list_reports(workspace_id: str, db: Session = Depends(get_db)):
    """List all reports (as thread DTOs) for a workspace."""
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    reports = report_service.list_reports(db, workspace_id)
    result = []
    for r in reports:
        msg_count = report_service.get_message_count(db, r.id)
        highlight = report_service.get_latest_highlight(db, r.id)
        result.append(
            _report_to_thread_out(
                r, message_count=msg_count, latest_highlight=highlight
            )
        )
    return result


@router.get("/reports/{report_id}")
def get_report_summary(report_id: str, db: Session = Depends(get_db)):
    """Get a report summary by ID."""
    report = report_service.get_report(db, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    msg_count = report_service.get_message_count(db, report_id)
    return _report_to_summary_out(report, message_count=msg_count)


# ── Report thread endpoints ──────────────────────────────────────────


@router.get("/report-threads/{thread_id}")
def get_thread_detail(thread_id: str, db: Session = Depends(get_db)):
    """Get thread metadata by ID."""
    report = report_service.get_report(db, thread_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    msg_count = report_service.get_message_count(db, thread_id)
    highlight = report_service.get_latest_highlight(db, thread_id)
    return _report_to_thread_out(
        report, message_count=msg_count, latest_highlight=highlight
    )


@router.get("/report-threads/{thread_id}/messages")
def get_thread_messages(thread_id: str, db: Session = Depends(get_db)):
    """Get all messages for a thread."""
    report = report_service.get_report(db, thread_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    messages = report_service.get_thread_messages(db, thread_id)
    return [_message_to_out(m) for m in messages]


@router.post("/report-threads/{thread_id}/messages", status_code=201)
def send_message(thread_id: str, body: MessageSendIn, db: Session = Depends(get_db)):
    """Send a feedback message and get an agent response."""
    report = report_service.get_report(db, thread_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Create user message
    user_msg = report_service.create_message(
        db,
        thread_id=thread_id,
        role="user",
        content=body.content,
    )

    # Create mocked agent response
    agent_msg = report_service.create_message(
        db,
        thread_id=thread_id,
        role="agent",
        content="Thank you for your feedback. We'll take this into account for future reports.",
        metadata_json={"model": "mock-agent", "tokens": 42},
    )

    db.commit()
    db.refresh(user_msg)
    db.refresh(agent_msg)

    return {
        "userMessage": _message_to_out(user_msg),
        "agentMessage": _message_to_out(agent_msg),
    }


@router.post("/report-messages/{message_id}/thumb")
def thumb_message(message_id: str, body: ThumbIn, db: Session = Depends(get_db)):
    """Toggle thumbs up/down on a message."""
    msg = report_service.get_message(db, message_id)
    if msg is None:
        raise HTTPException(status_code=404, detail="Message not found")

    # Toggle logic: if same vote, remove; if different, replace
    new_feedback: str | None = body.value
    if msg.feedback == body.value:
        new_feedback = None

    report_service.update_message_feedback(db, msg, new_feedback)

    # Create a feedback event
    feedback_type = "thumbs_up" if body.value == "up" else "thumbs_down"
    sentiment = "positive" if body.value == "up" else "negative"
    if new_feedback is None:
        sentiment = "neutral"
    feedback_service.create_feedback_event(
        db,
        workspace_id=msg.thread and msg.thread.workspace_id or "",
        feedback_type=feedback_type,
        sentiment=sentiment,
        thread_id=msg.thread_id,
        message_id=msg.id,
    )

    db.commit()
    db.refresh(msg)

    return {"success": True}


# ── Regenerate endpoint ──────────────────────────────────────────────


@router.post("/reports/{report_id}/regenerate")
def regenerate_report(report_id: str, db: Session = Depends(get_db)):
    """Regenerate a report using the real report generator.

    Creates a new Report and ReportMessage with fresh content, and marks
    the original agent message as regenerated with tracking metadata.
    """
    report = report_service.get_report(db, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    last_agent = report_service.get_last_agent_message(db, report_id)
    if last_agent is None:
        raise HTTPException(
            status_code=404, detail="No agent message found to regenerate"
        )

    # Get the workspace from the original report
    workspace = ws_service.get_workspace(db, report.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Get shortlisted content items for the workspace
    shortlisted_items = (
        db.query(ContentItem)
        .filter(
            ContentItem.workspace_id == workspace.id,
            ContentItem.status == "included",
        )
        .order_by(ContentItem.final_score.desc())
        .all()
    )

    # Create a new processing run for the regeneration
    new_run = ProcessingRun(
        workspace_id=workspace.id,
        run_type="manual",
        status="running",
    )
    db.add(new_run)
    db.flush()

    # Create OpenCode client if enabled
    opencode_client: OpenCodeClient | None = None
    if settings.OPENCODE_ENABLED:
        opencode_client = OpenCodeClient(
            base_url=settings.OPENCODE_BASE_URL,
            timeout=settings.OPENCODE_TIMEOUT_SECONDS,
            default_model=settings.OPENCODE_DEFAULT_MODEL,
            enabled=True,
        )

    # Generate a new report
    new_report = generate_report(
        db,
        workspace,
        shortlisted_items,
        new_run,
        opencode_client=opencode_client,
    )

    # Add regeneration tracking metadata to the new report's system message
    new_messages = report_service.get_thread_messages(db, new_report.id)
    system_msg = next((m for m in new_messages if m.role == "system"), None)
    if system_msg is not None:
        system_msg.metadata_json = {
            **(system_msg.metadata_json or {}),
            "regenerated": True,
            "originalMessageId": last_agent.id,
            "originalReportId": report_id,
        }

    # Mark the original agent message as regenerated
    metadata = {
        **(last_agent.metadata_json or {}),
        "regenerated": True,
        "originalMessageId": last_agent.id,
        "newReportId": new_report.id,
    }
    last_agent.metadata_json = metadata

    # Mark the new run as successful
    new_run.status = "success"

    db.commit()
    db.refresh(new_report)
    db.refresh(last_agent)
    if system_msg is not None:
        db.refresh(system_msg)

    # Return the new report's system message
    if system_msg is None:
        raise HTTPException(status_code=500, detail="Report generation failed")

    return _message_to_out(system_msg)
