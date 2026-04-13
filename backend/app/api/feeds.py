"""FeedSource API endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.feed import FeedCreate, FeedUpdate, FeedOut, _feed_to_out
from app.services import feed as feed_service
from app.services import workspace as ws_service
from app.services.pipeline_steps import validate_feed_source

router = APIRouter(prefix="/api", tags=["feeds"])


# ── Workspace-scoped feed endpoints ───────────────────────────────────


@router.get("/workspaces/{workspace_id}/feeds", response_model=list[FeedOut])
def list_feeds(workspace_id: str, db: Session = Depends(get_db)):
    """List all feeds for a workspace."""
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    feeds = feed_service.list_feeds(db, workspace_id)
    return [_feed_to_out(f) for f in feeds]


@router.post(
    "/workspaces/{workspace_id}/feeds", response_model=FeedOut, status_code=201
)
def create_feed(workspace_id: str, body: FeedCreate, db: Session = Depends(get_db)):
    """Create a new feed for a workspace."""
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    feed = feed_service.create_feed(
        db,
        workspace_id=workspace_id,
        name=body.name,
        url=body.url,
        type=body.type,
        cadence=body.cadence,
        tags=body.tags,
    )
    db.commit()
    db.refresh(feed)
    return _feed_to_out(feed)


# ── Feed-scoped endpoints ─────────────────────────────────────────────


@router.get("/feeds/{feed_id}", response_model=FeedOut)
def get_feed(feed_id: str, db: Session = Depends(get_db)):
    """Get a single feed by ID."""
    feed = feed_service.get_feed(db, feed_id)
    if feed is None:
        raise HTTPException(status_code=404, detail="Feed not found")
    return _feed_to_out(feed)


@router.patch("/feeds/{feed_id}", response_model=FeedOut)
def update_feed(feed_id: str, body: FeedUpdate, db: Session = Depends(get_db)):
    """Partially update a feed."""
    feed = feed_service.get_feed(db, feed_id)
    if feed is None:
        raise HTTPException(status_code=404, detail="Feed not found")

    feed_service.update_feed(
        db,
        feed,
        name=body.name,
        url=body.url,
        type=body.type,
        cadence=body.cadence,
        tags=body.tags,
    )
    db.commit()
    db.refresh(feed)
    return _feed_to_out(feed)


@router.delete("/feeds/{feed_id}", response_model=FeedOut)
def delete_feed(feed_id: str, db: Session = Depends(get_db)):
    """Soft-delete a feed by setting status to disabled."""
    feed = feed_service.delete_feed(db, feed_id)
    if feed is None:
        raise HTTPException(status_code=404, detail="Feed not found")

    return _feed_to_out(feed)


@router.post("/feeds/{feed_id}/toggle", response_model=FeedOut)
def toggle_feed(feed_id: str, db: Session = Depends(get_db)):
    """Toggle feed status between healthy and disabled."""
    feed = feed_service.get_feed(db, feed_id)
    if feed is None:
        raise HTTPException(status_code=404, detail="Feed not found")

    feed_service.toggle_feed_status(db, feed)
    db.commit()
    db.refresh(feed)
    return _feed_to_out(feed)


@router.post("/feeds/{feed_id}/test")
def test_feed(feed_id: str, db: Session = Depends(get_db)):
    """Fetch and parse a feed, returning the real validation result."""
    feed = feed_service.get_feed(db, feed_id)
    if feed is None:
        raise HTTPException(status_code=404, detail="Feed not found")

    result = validate_feed_source(feed)
    # Update fetch reliability counters
    feed.total_fetch_count = (feed.total_fetch_count or 0) + 1
    if result.success:
        feed.status = "healthy"
        feed.last_error = None
        feed.last_error_at = None
        feed.last_fetched_at = datetime.now(timezone.utc)
        feed.last_successful_fetch_at = datetime.now(timezone.utc)
        feed.consecutive_fetch_failures = 0
    else:
        feed.status = "error"
        feed.last_error = result.error
        feed.last_error_at = datetime.now(timezone.utc)
        feed.consecutive_fetch_failures = (feed.consecutive_fetch_failures or 0) + 1
    db.commit()
    db.refresh(feed)

    return {
        "success": result.success,
        "feedId": feed.id,
        "message": (
            f"Feed test completed successfully: parsed {result.articles_found} articles"
            if result.success
            else "Feed test failed"
        ),
        "articlesFound": result.articles_found,
        "sourceTitle": result.source_title,
        "lastFetchedAt": feed.last_fetched_at.isoformat()
        if feed.last_fetched_at
        else None,
        "lastError": result.error,
        "lastErrorAt": feed.last_error_at.isoformat() if feed.last_error_at else None,
    }
