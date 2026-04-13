"""FeedSource SQLAlchemy model."""

from sqlalchemy import String, Text, DateTime, JSON, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.workspace import _uuid, _now

# Default threshold for marking a feed as "stale": no successful fetch
# in this many consecutive fetch attempts.
DEFAULT_STALE_FETCH_THRESHOLD: int = 5


class FeedSource(Base):
    __tablename__ = "feed_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # rss, website, competitor, blog
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="healthy"
    )  # healthy, error, disabled
    last_fetched_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    cadence: Mapped[str] = mapped_column(
        String(20), nullable=False, default="daily"
    )  # hourly, daily, weekly
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    # Feed reliability tracking
    last_successful_fetch_at: Mapped[str | None] = mapped_column(
        DateTime, nullable=True
    )
    consecutive_fetch_failures: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_fetch_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[str | None] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", backref="feeds")

    # ── Computed properties ────────────────────────────────────────────

    @property
    def fetch_success_rate(self) -> float:
        """Return the fetch success rate (0.0 – 1.0).

        Returns 0.0 when no fetches have been attempted.
        """
        if self.total_fetch_count <= 0:
            return 0.0
        successes = self.total_fetch_count - self.consecutive_fetch_failures
        # Approximate: use total_fetch_count - consecutive as a lower-bound
        # for total successes.  This is correct when failures are always
        # consecutive (which is the common pattern: feed goes down, gets
        # fixed, goes down again).  A true running count would need a
        # separate column; this approximation is sufficient for scoring.
        # We use total_fetch_count as denominator so rate ∈ [0, 1].
        return max(0.0, min(1.0, successes / self.total_fetch_count))

    @property
    def is_stale(self, *, threshold: int = DEFAULT_STALE_FETCH_THRESHOLD) -> bool:
        """Return True if the feed is considered stale.

        A feed is stale when it has had more than *threshold* consecutive
        fetch failures and no successful fetch within that window.
        """
        if self.total_fetch_count < threshold:
            return False
        return self.consecutive_fetch_failures >= threshold
