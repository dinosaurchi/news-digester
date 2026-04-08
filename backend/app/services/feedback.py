"""Feedback business logic."""

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.report import FeedbackEvent, Report, ReportMessage


def list_feedback_events(db: Session, workspace_id: str) -> list[FeedbackEvent]:
    """Return all feedback events for a workspace, ordered by created_at desc."""
    return (
        db.query(FeedbackEvent)
        .filter(FeedbackEvent.workspace_id == workspace_id)
        .order_by(FeedbackEvent.created_at.desc())
        .all()
    )


def get_feedback_summary(db: Session, workspace_id: str) -> dict:
    """Compute a feedback summary for a workspace."""
    events = (
        db.query(FeedbackEvent).filter(FeedbackEvent.workspace_id == workspace_id).all()
    )

    total_events = len(events)
    thumbs_up = sum(1 for e in events if e.feedback_type == "thumbs_up")
    thumbs_down = sum(1 for e in events if e.feedback_type == "thumbs_down")
    net_sentiment = thumbs_up - thumbs_down

    # Aggregate topic_preferences
    topic_prefs: dict[str, dict] = {}
    for e in events:
        if e.feedback_type == "topic_preference" and e.value:
            if e.value not in topic_prefs:
                topic_prefs[e.value] = {
                    "topic": e.value,
                    "count": 0,
                    "sentiment": "neutral",
                }
            topic_prefs[e.value]["count"] += 1
            if e.sentiment:
                topic_prefs[e.value]["sentiment"] = e.sentiment
    topic_preferences = sorted(
        topic_prefs.values(), key=lambda x: x["count"], reverse=True
    )

    # Aggregate source_preferences
    source_prefs: dict[str, dict] = {}
    for e in events:
        if e.feedback_type == "source_preference" and e.value:
            if e.value not in source_prefs:
                source_prefs[e.value] = {
                    "source": e.value,
                    "count": 0,
                    "sentiment": "neutral",
                }
            source_prefs[e.value]["count"] += 1
            if e.sentiment:
                source_prefs[e.value]["sentiment"] = e.sentiment
    source_preferences = sorted(
        source_prefs.values(), key=lambda x: x["count"], reverse=True
    )

    return {
        "totalEvents": total_events,
        "thumbsUp": thumbs_up,
        "thumbsDown": thumbs_down,
        "netSentiment": net_sentiment,
        "topicPreferences": topic_preferences,
        "sourcePreferences": source_preferences,
        "reportStylePreferences": [],
    }


def create_feedback_event(
    db: Session,
    *,
    workspace_id: str,
    feedback_type: str,
    value: str | None = None,
    sentiment: str | None = None,
    thread_id: str | None = None,
    message_id: str | None = None,
) -> FeedbackEvent:
    """Create and persist a new feedback event."""
    event = FeedbackEvent(
        workspace_id=workspace_id,
        feedback_type=feedback_type,
        value=value,
        sentiment=sentiment,
        thread_id=thread_id,
        message_id=message_id,
    )
    db.add(event)
    db.flush()
    return event
