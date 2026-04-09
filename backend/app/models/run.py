"""ProcessingRun and ProcessingRunEvent SQLAlchemy models."""

from sqlalchemy import String, Text, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.workspace import _uuid, _now


class ProcessingRun(Base):
    __tablename__ = "processing_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # scheduled, manual
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="running"
    )  # success, failed, running
    started_at: Mapped[str] = mapped_column(DateTime, default=_now)
    finished_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    affected_counts_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # {feeds, articles, reports}
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[str | None] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    workspace: Mapped["Workspace"] = relationship(
        "Workspace", backref="processing_runs"
    )
    events: Mapped[list["ProcessingRunEvent"]] = relationship(
        "ProcessingRunEvent",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="ProcessingRunEvent.created_at",
    )


class ProcessingRunEvent(Base):
    __tablename__ = "processing_run_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("processing_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # pending, running, success, failed, skipped
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime, default=_now)

    run: Mapped["ProcessingRun"] = relationship(
        "ProcessingRun", back_populates="events"
    )
