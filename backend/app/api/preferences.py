"""Preference API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import preferences as pref_service
from app.services import workspace as ws_service

router = APIRouter(prefix="/api", tags=["preferences"])


# ── Request / Response schemas ─────────────────────────────────────────


class TopicPrefItem(BaseModel):
    topic: str
    weight: float = 1.0


class SourcePrefItem(BaseModel):
    source: str
    weight: float = 1.0


class EntityPrefItem(BaseModel):
    entity: str
    weight: float = 1.0


class TopicPrefRequest(BaseModel):
    preferences: list[TopicPrefItem]


class SourcePrefRequest(BaseModel):
    preferences: list[SourcePrefItem]


class EntityPrefRequest(BaseModel):
    preferences: list[EntityPrefItem]


class TopicPrefOut(BaseModel):
    id: str
    topic: str
    weight: float


class SourcePrefOut(BaseModel):
    id: str
    source: str
    weight: float


class EntityPrefOut(BaseModel):
    id: str
    entity: str
    weight: float


# ── Endpoints ──────────────────────────────────────────────────────────


@router.put("/workspaces/{workspace_id}/preferences/topics")
def put_topic_preferences(
    workspace_id: str, body: TopicPrefRequest, db: Session = Depends(get_db)
):
    """Replace all topic preferences for a workspace."""
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    prefs = pref_service._upsert_topic_preferences(
        db, workspace_id, [p.model_dump() for p in body.preferences]
    )
    db.commit()
    return [{"id": p.id, "topic": p.topic, "weight": p.weight} for p in prefs]


@router.put("/workspaces/{workspace_id}/preferences/sources")
def put_source_preferences(
    workspace_id: str, body: SourcePrefRequest, db: Session = Depends(get_db)
):
    """Replace all source preferences for a workspace."""
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    prefs = pref_service._upsert_source_preferences(
        db, workspace_id, [p.model_dump() for p in body.preferences]
    )
    db.commit()
    return [{"id": p.id, "source": p.source_name, "weight": p.weight} for p in prefs]


@router.put("/workspaces/{workspace_id}/preferences/entities")
def put_entity_preferences(
    workspace_id: str, body: EntityPrefRequest, db: Session = Depends(get_db)
):
    """Replace all entity preferences for a workspace."""
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    prefs = pref_service._upsert_entity_preferences(
        db, workspace_id, [p.model_dump() for p in body.preferences]
    )
    db.commit()
    return [{"id": p.id, "entity": p.entity_name, "weight": p.weight} for p in prefs]


@router.get("/workspaces/{workspace_id}/preferences/topics")
def get_topic_preferences(workspace_id: str, db: Session = Depends(get_db)):
    """Get all topic preferences for a workspace."""
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    prefs = pref_service.get_topic_preferences(db, workspace_id)
    return [{"id": p.id, "topic": p.topic, "weight": p.weight} for p in prefs]


@router.get("/workspaces/{workspace_id}/preferences/sources")
def get_source_preferences(workspace_id: str, db: Session = Depends(get_db)):
    """Get all source preferences for a workspace."""
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    prefs = pref_service.get_source_preferences(db, workspace_id)
    return [{"id": p.id, "source": p.source_name, "weight": p.weight} for p in prefs]


@router.get("/workspaces/{workspace_id}/preferences/entities")
def get_entity_preferences(workspace_id: str, db: Session = Depends(get_db)):
    """Get all entity preferences for a workspace."""
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    prefs = pref_service.get_entity_preferences(db, workspace_id)
    return [{"id": p.id, "entity": p.entity_name, "weight": p.weight} for p in prefs]
