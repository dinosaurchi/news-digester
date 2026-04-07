"""FeedSource business logic."""

from sqlalchemy.orm import Session

from app.models.feed import FeedSource


def list_feeds(db: Session, workspace_id: str) -> list[FeedSource]:
    """Return all feeds for a workspace, ordered by name."""
    return (
        db.query(FeedSource)
        .filter(FeedSource.workspace_id == workspace_id)
        .order_by(FeedSource.name)
        .all()
    )


def get_feed(db: Session, feed_id: str) -> FeedSource | None:
    """Return a single feed by ID, or None."""
    return db.query(FeedSource).filter(FeedSource.id == feed_id).first()


def create_feed(
    db: Session,
    *,
    workspace_id: str,
    name: str,
    url: str,
    type: str,
    cadence: str = "daily",
    tags: list[str] | None = None,
) -> FeedSource:
    """Create and persist a new feed source."""
    feed = FeedSource(
        workspace_id=workspace_id,
        name=name,
        url=url,
        type=type,
        status="healthy",
        cadence=cadence,
        tags=tags or [],
    )
    db.add(feed)
    db.flush()
    return feed


def update_feed(db: Session, feed: FeedSource, **kwargs) -> FeedSource:
    """Apply partial updates to a feed."""
    for key, value in kwargs.items():
        if value is not None:
            setattr(feed, key, value)
    db.flush()
    return feed


def delete_feed(db: Session, feed: FeedSource) -> None:
    """Hard-delete a feed source."""
    db.delete(feed)
    db.flush()


def toggle_feed_status(db: Session, feed: FeedSource) -> FeedSource:
    """Toggle feed status between healthy and disabled.

    If status is "disabled" → set to "healthy".
    If status is anything else (including "error") → set to "disabled".
    """
    if feed.status == "disabled":
        feed.status = "healthy"
    else:
        feed.status = "disabled"
    db.flush()
    return feed
