"""Feedback business logic."""

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.report import FeedbackEvent, Report, ReportMessage
from app.models.preferences import TopicPreference, SourcePreference


def list_feedback_events(db: Session, workspace_id: str) -> list[FeedbackEvent]:
    """Return all feedback events for a workspace, ordered by created_at desc."""
    return (
        db.query(FeedbackEvent)
        .filter(FeedbackEvent.workspace_id == workspace_id)
        .order_by(FeedbackEvent.created_at.desc())
        .all()
    )


def get_feedback_summary(db: Session, workspace_id: str) -> dict:
    """Compute a feedback summary for a workspace.

    topicPreferences and sourcePreferences are computed from the actual
    preference tables (TopicPreference / SourcePreference).  The feedback
    events aggregation is kept as a fallback so the summary still makes
    sense when no explicit preferences have been set.
    """
    events = (
        db.query(FeedbackEvent).filter(FeedbackEvent.workspace_id == workspace_id).all()
    )

    total_events = len(events)
    thumbs_up = sum(1 for e in events if e.feedback_type == "thumbs_up")
    thumbs_down = sum(1 for e in events if e.feedback_type == "thumbs_down")
    net_sentiment = thumbs_up - thumbs_down

    # ── Topic preferences from preference table ────────────────────────
    topic_prefs_from_table = (
        db.query(TopicPreference)
        .filter(TopicPreference.workspace_id == workspace_id)
        .order_by(TopicPreference.weight.desc())
        .all()
    )
    if topic_prefs_from_table:
        topic_preferences = [
            {
                "topic": tp.topic,
                "weight": tp.weight,
                "sentiment": "positive"
                if tp.weight > 0
                else ("negative" if tp.weight < 0 else "neutral"),
            }
            for tp in topic_prefs_from_table
        ]
    else:
        # Fallback: aggregate from feedback events
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

    # ── Source preferences from preference table ───────────────────────
    source_prefs_from_table = (
        db.query(SourcePreference)
        .filter(SourcePreference.workspace_id == workspace_id)
        .order_by(SourcePreference.weight.desc())
        .all()
    )
    if source_prefs_from_table:
        source_preferences = [
            {
                "source": sp.source_name,
                "weight": sp.weight,
                "sentiment": "positive"
                if sp.weight > 0
                else ("negative" if sp.weight < 0 else "neutral"),
            }
            for sp in source_prefs_from_table
        ]
    else:
        # Fallback: aggregate from feedback events
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


_FEEDBACK_WEIGHT_CAP = 5.0
_FEEDBACK_WEIGHT_DELTA = 1.0


def _upsert_preference_from_feedback(
    db: Session,
    *,
    workspace_id: str,
    model: type,
    lookup_field: str,
    lookup_value: str,
    sentiment: str | None,
) -> None:
    """Upsert a preference record from a feedback event using accumulative weight.

    - positive sentiment → add +1.0 to existing weight (or set 1.0 if new)
    - negative sentiment → add -1.0 to existing weight (or set -1.0 if new)
    - neutral / missing  → reset weight to 0.0

    Weight is capped at ±_FEEDBACK_WEIGHT_CAP.
    """
    existing = (
        db.query(model)
        .filter(
            model.workspace_id == workspace_id,
            getattr(model, lookup_field) == lookup_value,
        )
        .one_or_none()
    )

    if sentiment == "positive":
        delta = _FEEDBACK_WEIGHT_DELTA
    elif sentiment == "negative":
        delta = -_FEEDBACK_WEIGHT_DELTA
    else:
        delta = 0.0  # neutral or missing → reset

    if existing is not None:
        if delta == 0.0:
            existing.weight = 0.0
        else:
            existing.weight = max(
                -_FEEDBACK_WEIGHT_CAP,
                min(_FEEDBACK_WEIGHT_CAP, existing.weight + delta),
            )
    else:
        new_weight = delta if abs(delta) > 0 else 0.0
        existing = model(
            workspace_id=workspace_id,
            **{lookup_field: lookup_value},
            weight=new_weight,
        )
        db.add(existing)


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
    """Create and persist a new feedback event.

    For ``topic_preference`` and ``source_preference`` events the
    corresponding preference record is also created / updated so that the
    scoring pipeline can read it.
    """
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

    # ── Convert feedback events into preference records ───────────────
    if feedback_type == "topic_preference" and value:
        _upsert_preference_from_feedback(
            db,
            workspace_id=workspace_id,
            model=TopicPreference,
            lookup_field="topic",
            lookup_value=value,
            sentiment=sentiment,
        )
    elif feedback_type == "source_preference" and value:
        _upsert_preference_from_feedback(
            db,
            workspace_id=workspace_id,
            model=SourcePreference,
            lookup_field="source_name",
            lookup_value=value,
            sentiment=sentiment,
        )

    return event
