"""Reports API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
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
    """Stub: regenerate the last agent message in a report thread."""
    report = report_service.get_report(db, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    last_agent = report_service.get_last_agent_message(db, report_id)
    if last_agent is None:
        raise HTTPException(
            status_code=404, detail="No agent message found to regenerate"
        )

    # Store original message ID and mark as regenerated
    metadata = last_agent.metadata_json or {}
    metadata["regenerated"] = True
    metadata["originalMessageId"] = last_agent.id
    last_agent.content = "This is a regenerated report. The original content has been replaced with fresh analysis."
    last_agent.metadata_json = metadata

    db.commit()
    db.refresh(last_agent)

    return _message_to_out(last_agent)
