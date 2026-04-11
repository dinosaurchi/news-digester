"""Shared processing pipeline execution helpers."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.config import settings
from app.models.content import ContentItem
from app.models.feed import FeedSource
from app.models.report import Report
from app.models.run import ProcessingRun, ProcessingRunEvent
from app.models.workspace import Workspace
from app.services.clustering import cluster_content_items
from app.services.opencode_client import OpenCodeClient
from app.services.pipeline_steps import (
    FeedFetchResult,
    fetch_feed,
    normalize_content,
)
from app.services.report_generator import generate_report
from app.services.scoring import score_content_items
from app.services.shortlist import select_shortlist


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _start_event(
    db: Session, run_id: str, step_name: str, message: str
) -> ProcessingRunEvent:
    started_at = datetime.now(timezone.utc)
    event = ProcessingRunEvent(
        run_id=run_id,
        step_name=step_name,
        status="running",
        message=message,
        metadata_json={"started_at": _iso(started_at)},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def _finish_event(
    db: Session,
    event: ProcessingRunEvent,
    *,
    status: str,
    message: str,
    extra_metadata: dict | None = None,
) -> ProcessingRunEvent:
    completed_at = datetime.now(timezone.utc)
    metadata = {
        **(event.metadata_json or {}),
        "completed_at": _iso(completed_at),
        "duration_ms": _duration_ms(event.metadata_json or {}, completed_at),
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    event.status = status
    event.message = message
    event.metadata_json = metadata
    db.commit()
    db.refresh(event)
    return event


def _duration_ms(metadata: dict, completed_at: datetime) -> int | None:
    started_at_raw = metadata.get("started_at")
    if not started_at_raw:
        return None
    try:
        started_at = datetime.fromisoformat(started_at_raw)
    except ValueError:
        return None
    return int((completed_at - started_at).total_seconds() * 1000)


def execute_workspace_run(
    db: Session,
    workspace: Workspace,
    *,
    run_type: str = "manual",
) -> tuple[ProcessingRun, list[ContentItem], Report]:
    """Execute the current Pass 7 pipeline synchronously for one workspace."""
    now = datetime.now(timezone.utc)
    run = ProcessingRun(
        workspace_id=workspace.id,
        run_type=run_type,
        status="running",
        started_at=now,
        affected_counts_json={"feeds": 0, "articles": 0, "reports": 0},
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    feeds = (
        db.query(FeedSource)
        .filter(
            FeedSource.workspace_id == workspace.id,
            FeedSource.status != "disabled",
        )
        .all()
    )

    all_items: list[ContentItem] = []
    report: Report | None = None

    # --- Counters for ingestion tracking ---
    entries_fetched: int = 0
    entries_imported: int = 0
    entries_skipped: int = 0
    feeds_attempted: int = len(feeds)
    feeds_succeeded: int = 0
    feeds_failed: int = 0
    feed_details: list[dict] = []

    try:
        fetch_event = _start_event(db, run.id, "fetch_feeds", "Fetching feeds...")
        for feed in feeds:
            result = fetch_feed(feed)
            if not result.success:
                # Record failure state on the feed — do NOT update last_fetched_at
                feed.status = "error"
                feed.last_error = result.error
                feed.last_error_at = datetime.now(timezone.utc)
                logger.warning("Skipping feed %s: %s", feed.name, result.error)
                feeds_failed += 1
                feed_details.append(
                    {
                        "feed_id": str(feed.id),
                        "feed_name": feed.name,
                        "feed_url": feed.url,
                        "status": "error",
                        "entries_count": 0,
                        "error": result.error,
                    }
                )
                continue
            feeds_succeeded += 1
            # Record healthy/recovery state on the feed
            feed.status = "healthy"
            feed.last_error = None
            feed.last_error_at = None
            feed.last_fetched_at = datetime.now(timezone.utc)
            entries_fetched += len(result.entries)
            content_items, skipped = normalize_content(
                workspace.id, feed, result.entries, db=db
            )
            entries_imported += len(content_items)
            entries_skipped += skipped
            for item in content_items:
                db.add(item)
            all_items.extend(content_items)
            if skipped:
                logger.info(
                    "Skipped %d duplicate entries for feed %s", skipped, feed.name
                )
            feed_details.append(
                {
                    "feed_id": str(feed.id),
                    "feed_name": feed.name,
                    "feed_url": feed.url,
                    "status": "healthy",
                    "entries_count": len(result.entries),
                    "error": None,
                }
            )
        db.commit()

        # Aggregated counts dict — used for event metadata and run counts
        counts = {
            "entries_fetched": entries_fetched,
            "entries_imported": entries_imported,
            "entries_skipped": entries_skipped,
            "feeds_attempted": feeds_attempted,
            "feeds_succeeded": feeds_succeeded,
            "feeds_failed": feeds_failed,
            "feed_details": feed_details,
        }

        _finish_event(
            db,
            fetch_event,
            status="success",
            message=(
                f"Fetched {feeds_succeeded}/{feeds_attempted} feeds, "
                f"imported {entries_imported} articles "
                f"({entries_skipped} skipped)"
            ),
            extra_metadata=counts,
        )

        normalize_event = _start_event(
            db,
            run.id,
            "normalize_content",
            "Normalizing content...",
        )
        _finish_event(
            db,
            normalize_event,
            status="success",
            message=f"Normalized {len(all_items)} content items",
            extra_metadata={"content_items": len(all_items)},
        )

        cluster_event = _start_event(
            db,
            run.id,
            "cluster_content",
            "Clustering content items...",
        )
        try:
            cluster_stats = cluster_content_items(db, all_items, workspace.id)
            _finish_event(
                db,
                cluster_event,
                status="completed",
                message=(
                    f"Clustered {cluster_stats['items_clustered']} items "
                    f"into {cluster_stats['clusters_created']} clusters "
                    f"({cluster_stats['singleton_clusters']} singletons)"
                ),
                extra_metadata=cluster_stats,
            )
        except Exception as cluster_exc:
            _finish_event(
                db,
                cluster_event,
                status="error",
                message=f"Clustering failed: {cluster_exc}",
            )
            raise

        score_event = _start_event(db, run.id, "score_content", "Scoring content...")
        try:
            score_result = score_content_items(db, all_items, workspace)
            db.commit()
            _finish_event(
                db,
                score_event,
                status="completed",
                message=(
                    f"Scored {len(all_items)} items, "
                    f"{score_result['included_count']} included"
                ),
                extra_metadata={
                    "included_count": score_result["included_count"],
                    "excluded_count": score_result["excluded_count"],
                    "avg_score": score_result["avg_score"],
                },
            )
        except Exception as score_exc:
            _finish_event(
                db,
                score_event,
                status="error",
                message=f"Scoring failed: {score_exc}",
            )
            raise

        # ------------------------------------------------------------------
        # Shortlist step: select the final candidate set for report
        # ------------------------------------------------------------------
        # Create OpenCode client (shared by shortlist + report steps)
        opencode_client = OpenCodeClient(
            base_url=settings.OPENCODE_BASE_URL,
            timeout=settings.OPENCODE_TIMEOUT_SECONDS,
            default_model=settings.OPENCODE_DEFAULT_MODEL,
            default_agent=settings.OPENCODE_DEFAULT_AGENT,
            workspace_dir=settings.OPENCODE_WORKSPACE_DIR,
        )

        shortlist_event = _start_event(
            db,
            run.id,
            "select_shortlist",
            "Selecting shortlist...",
        )
        try:
            included_items = [item for item in all_items if item.status == "included"]

            shortlisted_items = select_shortlist(
                db, included_items, workspace, run, opencode_client=opencode_client
            )

            _finish_event(
                db,
                shortlist_event,
                status="completed",
                message=(
                    f"Shortlisted {len(shortlisted_items)} items "
                    f"from {len(included_items)} included"
                ),
                extra_metadata={
                    "shortlist_size": len(shortlisted_items),
                    "included_count": len(included_items),
                },
            )
        except Exception as shortlist_exc:
            _finish_event(
                db,
                shortlist_event,
                status="error",
                message=f"Shortlist selection failed: {shortlist_exc}",
            )
            raise

        # ------------------------------------------------------------------
        # Report generation step
        # ------------------------------------------------------------------
        report_event = _start_event(
            db,
            run.id,
            "generate_report",
            "Generating report...",
        )
        try:
            report = generate_report(
                db,
                workspace,
                shortlisted_items,
                run,
                opencode_client=opencode_client,
            )
            db.commit()
            db.refresh(report)

            _finish_event(
                db,
                report_event,
                status="success",
                message=f"Generated report: {report.title}",
                extra_metadata={
                    "report_id": report.id,
                    "item_count": len(shortlisted_items),
                },
            )
        except Exception as report_exc:
            _finish_event(
                db,
                report_event,
                status="error",
                message=f"Report generation failed: {report_exc}",
            )
            raise

        finished = datetime.now(timezone.utc)
        run.status = "success"
        run.finished_at = finished
        run.duration_ms = int((finished - now).total_seconds() * 1000)
        run.affected_counts_json = {
            "feeds": feeds_succeeded,
            "articles": entries_imported,
            "reports": 1,
            "entries_skipped": entries_skipped,
        }
        db.commit()
        db.refresh(run)
        return run, all_items, report

    except Exception as exc:
        finished = datetime.now(timezone.utc)
        run.status = "failed"
        run.finished_at = finished
        run.duration_ms = int((finished - now).total_seconds() * 1000)
        run.error_summary = str(exc)
        db.commit()
        db.refresh(run)
        raise
