import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    profile: Mapped["WorkspaceProfile | None"] = relationship(
        "WorkspaceProfile",
        back_populates="workspace",
        uselist=False,
        cascade="all, delete-orphan",
    )
    settings: Mapped["WorkspaceSettings | None"] = relationship(
        "WorkspaceSettings",
        back_populates="workspace",
        uselist=False,
        cascade="all, delete-orphan",
    )


class WorkspaceProfile(Base):
    __tablename__ = "workspace_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    business_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    products: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    competitors: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    priority_themes: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=list
    )
    excluded_topics: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=list
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="profile")


class WorkspaceSettings(Base):
    __tablename__ = "workspace_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    schedule: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    report_style: Mapped[str] = mapped_column(
        String(20), nullable=False, default="detailed"
    )
    thresholds: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    retention: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    email_delivery: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=dict
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    workspace: Mapped["Workspace"] = relationship(
        "Workspace", back_populates="settings"
    )
