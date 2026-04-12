"""Content business logic."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.content import ContentItem


class NotFoundError(Exception):
    """Raised when a requested content item does not exist."""


def list_content(
    db: Session,
    workspace_id: str,
    *,
    status: str | None = None,
    content_type: str | None = None,
    source: str | None = None,
    min_score: float | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[ContentItem]:
    """Return content items for a workspace with optional filters, ordered by published_at desc."""
    q = db.query(ContentItem).filter(ContentItem.workspace_id == workspace_id)

    if status is not None:
        q = q.filter(ContentItem.status == status)
    if content_type is not None:
        q = q.filter(ContentItem.content_type == content_type)
    if source is not None:
        q = q.filter(ContentItem.source_name == source)
    if min_score is not None:
        q = q.filter(ContentItem.final_score >= min_score)
    if date_from is not None:
        q = q.filter(ContentItem.published_at >= date_from)
    if date_to is not None:
        q = q.filter(ContentItem.published_at <= date_to)

    return q.order_by(ContentItem.published_at.desc()).all()


def get_content_item(db: Session, content_id: str) -> ContentItem | None:
    """Return a single content item by ID, or None."""
    return db.query(ContentItem).filter(ContentItem.id == content_id).first()


def get_cluster_items(db: Session, cluster_id: str) -> list[ContentItem]:
    """Return all content items sharing the same cluster_id."""
    if cluster_id is None:
        return []
    return (
        db.query(ContentItem)
        .filter(ContentItem.cluster_id == cluster_id)
        .order_by(ContentItem.published_at.desc())
        .all()
    )


def build_score_breakdown(item: ContentItem) -> dict:
    """Return scoreBreakdown for a content item from persisted score data.

    Reads from ``item.score_breakdown_json`` which is populated by the scoring
    pipeline.  Falls back to ``local_relevance_score`` / ``llm_score`` for
    items that have not yet been scored by the new pipeline, and returns zeros
    for components that have no persisted value.
    """
    breakdown = item.score_breakdown_json
    if breakdown and "scores" in breakdown:
        scores = breakdown["scores"]
        return {
            "relevance": round(float(scores.get("keyword", 0)), 4),
            "llm": round(float(scores.get("bm25", 0)), 4),
            "freshness": round(float(scores.get("freshness", 0)), 4),
            "sourceAuthority": round(float(scores.get("source_authority", 0)), 4),
        }
    # Fallback for items not yet scored by the new pipeline
    return {
        "relevance": item.local_relevance_score or 0,
        "llm": item.llm_score or 0,
        "freshness": 0,
        "sourceAuthority": 0,
    }


def delete_content_item(db: Session, item_id: str) -> None:
    """Delete a content item by ID.

    Raises ``NotFoundError`` if the item does not exist.
    """
    item = db.get(ContentItem, item_id)
    if item is None:
        raise NotFoundError(f"Content item {item_id} not found")
    db.delete(item)
    db.commit()
