"""Report, ReportMessage, and FeedbackEvent SQLAlchemy models."""

from sqlalchemy import String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.workspace import _uuid, _now


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    period_start: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    period_end: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    markdown_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    published_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[str | None] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", backref="reports")
    messages: Mapped[list["ReportMessage"]] = relationship(
        "ReportMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="ReportMessage.created_at",
    )


class ReportMessage(Base):
    __tablename__ = "report_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    thread_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # system, user, agent
    content: Mapped[str] = mapped_column(Text, nullable=False)
    feedback: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # up, down, null
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    parent_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    sent_at: Mapped[str] = mapped_column(DateTime, default=_now)
    created_at: Mapped[str] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[str | None] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    thread: Mapped["Report"] = relationship("Report", back_populates="messages")


class FeedbackEvent(Base):
    __tablename__ = "feedback_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    report_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    thread_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    content_item_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    feedback_type: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime, default=_now)

    workspace: Mapped["Workspace"] = relationship(
        "Workspace", backref="feedback_events"
    )
