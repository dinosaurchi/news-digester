"""ContentItem and ContentCluster SQLAlchemy models."""

from sqlalchemy import String, Text, DateTime, JSON, Float, ForeignKey, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.workspace import _uuid, _now


class ContentItem(Base):
    __tablename__ = "content_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    feed_source_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("feed_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # news, article, press_release, blog, competitor, social
    published_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    local_relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    llm_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_breakdown_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_lead: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # included, excluded, pending
    cluster_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("content_clusters.id", ondelete="SET NULL"),
        nullable=True,
    )
    inclusion_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    exclusion_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_entry_id: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[str | None] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", backref="content_items")
    cluster: Mapped["ContentCluster | None"] = relationship(
        "ContentCluster", back_populates="items", foreign_keys=[cluster_id]
    )


class ContentCluster(Base):
    __tablename__ = "content_clusters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str | None] = mapped_column(String(500), nullable=True)
    item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[str | None] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    items: Mapped[list[ContentItem]] = relationship(
        "ContentItem", back_populates="cluster", lazy="dynamic"
    )
    workspace: Mapped["Workspace"] = relationship(
        "Workspace", backref="content_clusters"
    )
