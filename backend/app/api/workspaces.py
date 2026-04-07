from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceOut,
    WorkspaceProfileIn,
    WorkspaceProfileOut,
    WorkspaceSettingsIn,
    WorkspaceSettingsOut,
)
from app.services import workspace as ws_service

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


def _ws_to_out(ws) -> dict:
    """Convert a Workspace ORM object to WorkspaceOut-compatible dict with camelCase keys."""
    return {
        "id": ws.id,
        "name": ws.name,
        "customer": ws.customer,
        "status": ws.status,
        "createdAt": ws.created_at.isoformat() if ws.created_at else None,
        "updatedAt": ws.updated_at.isoformat() if ws.updated_at else None,
        "feedCount": 0,  # computed — will be 0 until feeds table exists
        "lastReportAt": None,  # computed — will be None until reports table exists
        "nextRunAt": None,  # computed — will be None until runs table exists
    }


def _profile_to_out(p) -> dict:
    """Convert a WorkspaceProfile ORM object to camelCase dict."""
    return {
        "id": p.id,
        "workspaceId": p.workspace_id,
        "businessName": p.business_name or "",
        "description": p.description or "",
        "products": p.products or [],
        "competitors": p.competitors or [],
        "priorityThemes": p.priority_themes or [],
        "excludedTopics": p.excluded_topics or [],
        "notes": p.notes or "",
        "updatedAt": p.updated_at.isoformat() if p.updated_at else None,
    }


def _settings_to_out(s) -> dict:
    """Convert a WorkspaceSettings ORM object to camelCase dict."""
    return {
        "id": s.id,
        "workspaceId": s.workspace_id,
        "schedule": s.schedule
        or {
            "enabled": False,
            "frequency": "daily",
            "timeOfDay": "08:00",
            "timezone": "UTC",
        },
        "reportStyle": s.report_style,
        "thresholds": s.thresholds
        or {
            "minRelevanceScore": 0.65,
            "minFinalScore": 0.70,
            "maxArticlesPerReport": 15,
        },
        "retention": s.retention
        or {
            "contentDays": 90,
            "reportDays": 365,
            "runHistoryDays": 180,
        },
        "emailDelivery": s.email_delivery
        or {
            "enabled": False,
            "recipients": [],
            "subjectPrefix": "[Intel Report]",
        },
        "updatedAt": s.updated_at.isoformat() if s.updated_at else None,
    }


# ── Workspace CRUD ───────────────────────────────────────────────────


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(db: Session = Depends(get_db)):
    workspaces = ws_service.list_workspaces(db)
    return [_ws_to_out(ws) for ws in workspaces]


@router.post("", response_model=WorkspaceOut, status_code=201)
def create_workspace(body: WorkspaceCreate, db: Session = Depends(get_db)):
    ws = ws_service.create_workspace(
        db,
        name=body.name,
        customer=body.customer,
        status=body.status,
    )
    db.commit()
    db.refresh(ws)
    return _ws_to_out(ws)


@router.get("/{workspace_id}", response_model=WorkspaceOut)
def get_workspace(workspace_id: str, db: Session = Depends(get_db)):
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return _ws_to_out(ws)


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
def update_workspace(
    workspace_id: str, body: WorkspaceUpdate, db: Session = Depends(get_db)
):
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    ws_service.update_workspace(
        db,
        ws,
        name=body.name,
        customer=body.customer,
        status=body.status,
    )
    db.commit()
    db.refresh(ws)
    return _ws_to_out(ws)


@router.delete("/{workspace_id}", response_model=WorkspaceOut)
def delete_workspace(workspace_id: str, db: Session = Depends(get_db)):
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    ws_service.soft_delete_workspace(db, ws)
    db.commit()
    db.refresh(ws)
    return _ws_to_out(ws)


# ── Profile endpoints ────────────────────────────────────────────────


@router.get("/{workspace_id}/profile", response_model=WorkspaceProfileOut)
def get_profile(workspace_id: str, db: Session = Depends(get_db)):
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    profile = ws_service.get_or_create_profile(db, workspace_id)
    db.commit()
    db.refresh(profile)
    return _profile_to_out(profile)


@router.put("/{workspace_id}/profile", response_model=WorkspaceProfileOut)
def put_profile(
    workspace_id: str, body: WorkspaceProfileIn, db: Session = Depends(get_db)
):
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    profile = ws_service.update_profile(
        db,
        workspace_id,
        business_name=body.business_name,
        description=body.description,
        products=body.products,
        competitors=body.competitors,
        priority_themes=body.priority_themes,
        excluded_topics=body.excluded_topics,
        notes=body.notes,
    )
    db.commit()
    db.refresh(profile)
    return _profile_to_out(profile)


# ── Settings endpoints ───────────────────────────────────────────────


@router.get("/{workspace_id}/settings", response_model=WorkspaceSettingsOut)
def get_settings(workspace_id: str, db: Session = Depends(get_db)):
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    settings = ws_service.get_or_create_settings(db, workspace_id)
    db.commit()
    db.refresh(settings)
    return _settings_to_out(settings)


@router.put("/{workspace_id}/settings", response_model=WorkspaceSettingsOut)
def put_settings(
    workspace_id: str, body: WorkspaceSettingsIn, db: Session = Depends(get_db)
):
    ws = ws_service.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    update_data = {}
    if body.schedule is not None:
        update_data["schedule"] = body.schedule.model_dump(by_alias=True)
    if body.report_style is not None:
        update_data["report_style"] = body.report_style
    if body.thresholds is not None:
        update_data["thresholds"] = body.thresholds.model_dump(by_alias=True)
    if body.retention is not None:
        update_data["retention"] = body.retention.model_dump(by_alias=True)
    if body.email_delivery is not None:
        update_data["email_delivery"] = body.email_delivery.model_dump(by_alias=True)

    settings = ws_service.update_settings(db, workspace_id, **update_data)
    db.commit()
    db.refresh(settings)
    return _settings_to_out(settings)
