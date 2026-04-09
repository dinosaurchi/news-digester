"""Preference business logic."""

from sqlalchemy.orm import Session

from app.models.preferences import TopicPreference, SourcePreference, EntityPreference


def _upsert_topic_preferences(
    db: Session, workspace_id: str, preferences: list[dict]
) -> list[TopicPreference]:
    """Replace all topic preferences for a workspace."""
    db.query(TopicPreference).filter(
        TopicPreference.workspace_id == workspace_id
    ).delete()
    db.flush()

    created = []
    for pref in preferences:
        tp = TopicPreference(
            workspace_id=workspace_id,
            topic=pref["topic"],
            weight=pref.get("weight", 1.0),
        )
        db.add(tp)
        created.append(tp)
    db.flush()
    return created


def _upsert_source_preferences(
    db: Session, workspace_id: str, preferences: list[dict]
) -> list[SourcePreference]:
    """Replace all source preferences for a workspace."""
    db.query(SourcePreference).filter(
        SourcePreference.workspace_id == workspace_id
    ).delete()
    db.flush()

    created = []
    for pref in preferences:
        sp = SourcePreference(
            workspace_id=workspace_id,
            source_name=pref["source"],
            weight=pref.get("weight", 1.0),
        )
        db.add(sp)
        created.append(sp)
    db.flush()
    return created


def _upsert_entity_preferences(
    db: Session, workspace_id: str, preferences: list[dict]
) -> list[EntityPreference]:
    """Replace all entity preferences for a workspace."""
    db.query(EntityPreference).filter(
        EntityPreference.workspace_id == workspace_id
    ).delete()
    db.flush()

    created = []
    for pref in preferences:
        ep = EntityPreference(
            workspace_id=workspace_id,
            entity_name=pref["entity"],
            weight=pref.get("weight", 1.0),
        )
        db.add(ep)
        created.append(ep)
    db.flush()
    return created


def get_topic_preferences(db: Session, workspace_id: str) -> list[TopicPreference]:
    """Return all topic preferences for a workspace."""
    return (
        db.query(TopicPreference)
        .filter(TopicPreference.workspace_id == workspace_id)
        .order_by(TopicPreference.weight.desc())
        .all()
    )


def get_source_preferences(db: Session, workspace_id: str) -> list[SourcePreference]:
    """Return all source preferences for a workspace."""
    return (
        db.query(SourcePreference)
        .filter(SourcePreference.workspace_id == workspace_id)
        .order_by(SourcePreference.weight.desc())
        .all()
    )


def get_entity_preferences(db: Session, workspace_id: str) -> list[EntityPreference]:
    """Return all entity preferences for a workspace."""
    return (
        db.query(EntityPreference)
        .filter(EntityPreference.workspace_id == workspace_id)
        .order_by(EntityPreference.weight.desc())
        .all()
    )
