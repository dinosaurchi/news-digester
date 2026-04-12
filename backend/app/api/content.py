"""Content API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.content import _content_item_to_out
from app.services import content as content_service
from app.services import workspace as ws_service
from app.services.content import NotFoundError
from app.services.session import get_current_user

router = APIRouter(prefix="/api", tags=["content"])


# ── Workspace-scoped content endpoints ────────────────────────────────


@router.get("/workspaces/{workspace_id}/content")
def list_content(
    workspace_id: str,
    status: str | None = Query(default=None),
    type: str | None = Query(default=None),
    source: str | None = Query(default=None),
    minScore: float | None = Query(default=None),
    dateFrom: str | None = Query(default=None),
    dateTo: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """List content items for a workspace with optional filters."""
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Parse date strings
    dt_from = None
    dt_to = None
    if dateFrom:
        try:
            dt_from = datetime.fromisoformat(dateFrom)
        except (ValueError, TypeError):
            raise HTTPException(status_code=422, detail="Invalid dateFrom format")
    if dateTo:
        try:
            dt_to = datetime.fromisoformat(dateTo)
        except (ValueError, TypeError):
            raise HTTPException(status_code=422, detail="Invalid dateTo format")

    items = content_service.list_content(
        db,
        workspace_id,
        status=status,
        content_type=type,
        source=source,
        min_score=minScore,
        date_from=dt_from,
        date_to=dt_to,
    )
    return [_content_item_to_out(item) for item in items]


# ── Content-scoped endpoints ──────────────────────────────────────────


@router.get("/content/{content_item_id}")
def get_content_detail(content_item_id: str, db: Session = Depends(get_db)):
    """Get a single content item by ID with detail (scoreBreakdown, clusterItems)."""
    item = content_service.get_content_item(db, content_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Content item not found")

    out = _content_item_to_out(item)

    # Add scoreBreakdown
    out["scoreBreakdown"] = content_service.build_score_breakdown(item)

    # Add clusterItems if item has a cluster
    cluster_items = content_service.get_cluster_items(db, item.cluster_id)
    if cluster_items:
        out["clusterItems"] = [
            _content_item_to_out(ci) for ci in cluster_items if ci.id != item.id
        ]

    return out


@router.delete("/content/{content_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content_item(
    content_item_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Delete a content item by ID. Requires authentication."""
    try:
        content_service.delete_content_item(db, content_item_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Content item not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
