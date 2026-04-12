"""Reports API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.models.content import ContentItem
from app.models.report import ReportMessage
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
from app.services import report_chat as report_chat_service
from app.services.content import NotFoundError
from app.services.opencode_client import (
    OpenCodeClient,
    OpenCodeResponseError,
    OpenCodeTimeoutError,
    OpenCodeUnavailableError,
)
from app.services.report_generator import render_report_markdown
from app.services.session import get_current_user

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


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Delete a report by ID. Requires authentication."""
    try:
        report_service.delete_report(db, report_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Report not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    """Send a report-chat message and get a configured assistant response."""
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
    db.commit()
    db.refresh(user_msg)

    workspace = ws_service.get_workspace(db, report.workspace_id)

    messages = report_service.get_thread_messages(db, thread_id)
    source_ids = report_chat_service.get_report_chat_source_ids(report, messages)
    source_items = report_chat_service.load_report_chat_source_items(
        db,
        workspace_id=report.workspace_id,
        source_ids=source_ids,
    )
    recent_messages = report_chat_service.recent_report_chat_messages(messages)

    opencode_client = OpenCodeClient(
        base_url=settings.OPENCODE_BASE_URL,
        timeout=settings.OPENCODE_TIMEOUT_SECONDS,
        default_model=settings.OPENCODE_DEFAULT_MODEL,
        default_agent=settings.OPENCODE_DEFAULT_AGENT,
        workspace_dir=settings.OPENCODE_WORKSPACE_DIR,
    )
    try:
        chat_result = report_chat_service.generate_report_chat_reply(
            client=opencode_client,
            question=body.content,
            report=report,
            workspace=workspace,
            source_items=source_items,
            recent_messages=recent_messages,
        )
    except OpenCodeUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OpenCodeTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except OpenCodeResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    metadata = {
        "model": chat_result.model,
        "sources": [item.id for item in source_items],
        "usage": chat_result.usage,
    }
    if chat_result.session_id:
        metadata["opencodeSessionId"] = chat_result.session_id

    agent_msg = report_service.create_message(
        db,
        thread_id=thread_id,
        role="agent",
        content=chat_result.content,
        metadata_json=metadata,
    )

    db.commit()
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
    """Regenerate a report message in the existing report thread.

    Appends a new generated ``system`` message, updates the report markdown,
    and marks the previous generated message as regenerated. Keeping the same
    thread ID matches the frontend's thread-scoped regenerate behavior.
    """
    report = report_service.get_report(db, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    original_msg = report_service.get_last_generated_message(db, report_id)

    # Get the workspace from the original report
    workspace = ws_service.get_workspace(db, report.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Regenerate from the original report/message sources. Falling back to a
    # capped current shortlist keeps regeneration bounded if old metadata is
    # absent (for example, legacy seeded report threads).
    source_ids = _report_source_ids(report.metadata_json)
    if not source_ids and original_msg is not None:
        source_ids = _report_source_ids(original_msg.metadata_json)

    if source_ids:
        items_by_id = {
            item.id: item
            for item in (
                db.query(ContentItem)
                .filter(
                    ContentItem.workspace_id == workspace.id,
                    ContentItem.id.in_(source_ids),
                )
                .all()
            )
        }
        shortlisted_items = [
            items_by_id[item_id] for item_id in source_ids if item_id in items_by_id
        ]
    else:
        shortlisted_items = (
            db.query(ContentItem)
            .filter(
                ContentItem.workspace_id == workspace.id,
                ContentItem.status == "included",
            )
            .order_by(ContentItem.final_score.desc())
            .limit(15)
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

    # Create OpenCode client
    opencode_client = OpenCodeClient(
        base_url=settings.OPENCODE_BASE_URL,
        timeout=settings.OPENCODE_TIMEOUT_SECONDS,
        default_model=settings.OPENCODE_DEFAULT_MODEL,
        default_agent=settings.OPENCODE_DEFAULT_AGENT,
        workspace_dir=settings.OPENCODE_WORKSPACE_DIR,
    )

    # Generate fresh markdown — fail explicitly if OpenCode is unavailable.
    try:
        markdown = render_report_markdown(
            workspace,
            shortlisted_items,
            opencode_client=opencode_client,
        )
    except OpenCodeUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OpenCodeTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except OpenCodeResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    source_ids = [item.id for item in shortlisted_items]
    metadata = {
        "regenerated": True,
        "originalMessageId": original_msg.id if original_msg is not None else None,
        "originalReportId": report_id,
        "reportId": report_id,
        "sources": source_ids,
    }
    regenerated_msg = ReportMessage(
        thread_id=report_id,
        role="system",
        content=markdown,
        metadata_json=metadata,
    )
    db.add(regenerated_msg)
    db.flush()

    if original_msg is not None:
        original_msg.metadata_json = {
            **(original_msg.metadata_json or {}),
            "regenerated": True,
            "originalMessageId": original_msg.id,
            "regeneratedMessageId": regenerated_msg.id,
        }

    report.markdown_body = markdown
    report.run_id = new_run.id
    new_run.status = "success"

    db.commit()
    db.refresh(regenerated_msg)

    return _message_to_out(regenerated_msg)


def _report_source_ids(metadata: dict | None) -> list[str]:
    """Return ordered source IDs from report/message metadata."""
    raw_sources = (metadata or {}).get("sources")
    if not isinstance(raw_sources, list):
        return []
    return [source_id for source_id in raw_sources if isinstance(source_id, str)]
