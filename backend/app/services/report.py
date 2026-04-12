"""Report business logic."""

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.report import Report, ReportMessage
from app.services.content import NotFoundError


def list_reports(db: Session, workspace_id: str) -> list[Report]:
    """Return all reports for a workspace, ordered by created_at desc."""
    return (
        db.query(Report)
        .filter(Report.workspace_id == workspace_id)
        .order_by(Report.created_at.desc())
        .all()
    )


def get_report(db: Session, report_id: str) -> Report | None:
    """Return a single report by ID, or None."""
    return db.query(Report).filter(Report.id == report_id).first()


def get_message_count(db: Session, thread_id: str) -> int:
    """Return the message count for a thread."""
    return (
        db.query(func.count(ReportMessage.id))
        .filter(ReportMessage.thread_id == thread_id)
        .scalar()
        or 0
    )


def get_latest_highlight(db: Session, thread_id: str) -> str | None:
    """Return the latest agent message content as a highlight."""
    msg = (
        db.query(ReportMessage)
        .filter(ReportMessage.thread_id == thread_id, ReportMessage.role == "agent")
        .order_by(ReportMessage.created_at.desc())
        .first()
    )
    if msg is None:
        return None
    # Return first ~100 chars as highlight
    content = msg.content
    if len(content) > 100:
        return content[:100] + "..."
    return content


def get_thread_messages(db: Session, thread_id: str) -> list[ReportMessage]:
    """Return all messages for a thread, ordered by created_at."""
    return (
        db.query(ReportMessage)
        .filter(ReportMessage.thread_id == thread_id)
        .order_by(ReportMessage.created_at)
        .all()
    )


def get_message(db: Session, message_id: str) -> ReportMessage | None:
    """Return a single message by ID, or None."""
    return db.query(ReportMessage).filter(ReportMessage.id == message_id).first()


def create_message(
    db: Session,
    *,
    thread_id: str,
    role: str,
    content: str,
    metadata_json: dict | None = None,
) -> ReportMessage:
    """Create and persist a new report message."""
    msg = ReportMessage(
        thread_id=thread_id,
        role=role,
        content=content,
        metadata_json=metadata_json,
    )
    db.add(msg)
    db.flush()
    return msg


def update_message_feedback(
    db: Session, message: ReportMessage, feedback: str | None
) -> ReportMessage:
    """Update the feedback field on a message."""
    message.feedback = feedback
    db.flush()
    return message


def get_last_agent_message(db: Session, thread_id: str) -> ReportMessage | None:
    """Return the last agent message in a thread."""
    return (
        db.query(ReportMessage)
        .filter(ReportMessage.thread_id == thread_id, ReportMessage.role == "agent")
        .order_by(ReportMessage.created_at.desc())
        .first()
    )


def get_last_generated_message(db: Session, thread_id: str) -> ReportMessage | None:
    """Return the latest generated report/agent message in a thread."""
    return (
        db.query(ReportMessage)
        .filter(
            ReportMessage.thread_id == thread_id,
            ReportMessage.role.in_(("system", "agent")),
        )
        .order_by(ReportMessage.created_at.desc())
        .first()
    )


def delete_report(db: Session, report_id: str) -> None:
    """Delete a report by ID.

    Raises ``NotFoundError`` if the report does not exist.  Child
    ``ReportMessage`` rows are cascade-deleted automatically.
    """
    report = db.get(Report, report_id)
    if report is None:
        raise NotFoundError(f"Report {report_id} not found")
    db.delete(report)
    db.commit()
