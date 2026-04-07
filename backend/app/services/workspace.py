"""Workspace business logic."""

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.workspace import Workspace, WorkspaceProfile, WorkspaceSettings


def list_workspaces(db: Session) -> list[Workspace]:
    """Return all workspaces ordered by name."""
    return db.query(Workspace).order_by(Workspace.name).all()


def get_workspace(db: Session, workspace_id: str) -> Workspace | None:
    """Return a single workspace by ID, or None."""
    return db.query(Workspace).filter(Workspace.id == workspace_id).first()


def create_workspace(
    db: Session, *, name: str, customer: str, status: str = "active"
) -> Workspace:
    """Create and persist a new workspace."""
    ws = Workspace(name=name, customer=customer, status=status)
    db.add(ws)
    db.flush()  # get the id
    return ws


def update_workspace(db: Session, workspace: Workspace, **kwargs) -> Workspace:
    """Apply partial updates to a workspace."""
    for key, value in kwargs.items():
        if value is not None:
            setattr(workspace, key, value)
    db.flush()
    return workspace


def soft_delete_workspace(db: Session, workspace: Workspace) -> Workspace:
    """Set workspace status to 'archived'."""
    workspace.status = "archived"
    db.flush()
    return workspace


def get_or_create_profile(db: Session, workspace_id: str) -> WorkspaceProfile:
    """Return the profile for a workspace, creating a default if missing."""
    profile = (
        db.query(WorkspaceProfile)
        .filter(WorkspaceProfile.workspace_id == workspace_id)
        .first()
    )
    if profile is None:
        profile = WorkspaceProfile(workspace_id=workspace_id)
        db.add(profile)
        db.flush()
    return profile


def update_profile(db: Session, workspace_id: str, **kwargs) -> WorkspaceProfile:
    """Replace profile fields for a workspace (upsert semantics)."""
    profile = get_or_create_profile(db, workspace_id)
    for key, value in kwargs.items():
        if value is not None:
            setattr(profile, key, value)
    db.flush()
    return profile


def get_or_create_settings(db: Session, workspace_id: str) -> WorkspaceSettings:
    """Return settings for a workspace, creating defaults if missing."""
    settings = (
        db.query(WorkspaceSettings)
        .filter(WorkspaceSettings.workspace_id == workspace_id)
        .first()
    )
    if settings is None:
        settings = WorkspaceSettings(
            workspace_id=workspace_id,
            schedule={
                "enabled": False,
                "frequency": "daily",
                "timeOfDay": "08:00",
                "timezone": "UTC",
            },
            report_style="detailed",
            thresholds={
                "minRelevanceScore": 0.65,
                "minFinalScore": 0.70,
                "maxArticlesPerReport": 15,
            },
            retention={
                "contentDays": 90,
                "reportDays": 365,
                "runHistoryDays": 180,
            },
            email_delivery={
                "enabled": False,
                "recipients": [],
                "subjectPrefix": "[Intel Report]",
            },
        )
        db.add(settings)
        db.flush()
    return settings


def update_settings(db: Session, workspace_id: str, **kwargs) -> WorkspaceSettings:
    """Replace settings fields for a workspace (upsert semantics)."""
    settings = get_or_create_settings(db, workspace_id)
    for key, value in kwargs.items():
        if value is not None:
            setattr(settings, key, value)
    db.flush()
    return settings
