"""TopicPreference, SourcePreference, and EntityPreference SQLAlchemy models."""

from sqlalchemy import String, DateTime, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.workspace import _uuid, _now


class TopicPreference(Base):
    __tablename__ = "topic_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[str] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[str | None] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )


class SourcePreference(Base):
    __tablename__ = "source_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[str] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[str | None] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )


class EntityPreference(Base):
    __tablename__ = "entity_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_name: Mapped[str] = mapped_column(String(255), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[str] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[str | None] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )
