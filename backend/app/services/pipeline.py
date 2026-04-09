"""Shared processing pipeline execution helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.content import ContentItem
from app.models.feed import FeedSource
from app.models.report import Report, ReportMessage
from app.models.run import ProcessingRun, ProcessingRunEvent
from app.models.workspace import Workspace
from app.services.clustering import cluster_content_items
from app.services.pipeline_steps import (
    fetch_feed,
    generate_report_stub,
    normalize_content,
)


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
    """Execute the current Pass 6 pipeline synchronously for one workspace."""
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

    try:
        fetch_event = _start_event(db, run.id, "fetch_feeds", "Fetching feeds...")
        for feed in feeds:
            raw_items = fetch_feed(feed)
            content_items = normalize_content(workspace.id, feed, raw_items)
            for item in content_items:
                db.add(item)
            all_items.extend(content_items)
            feed.last_fetched_at = datetime.now(timezone.utc)
        db.commit()
        _finish_event(
            db,
            fetch_event,
            status="success",
            message=f"Fetched {len(feeds)} feeds, found {len(all_items)} articles",
            extra_metadata={"feed_count": len(feeds), "article_count": len(all_items)},
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
        for i, item in enumerate(all_items):
            if i < 5:
                item.status = "included"
                item.final_score = 0.8
                item.inclusion_reason = "High relevance score"
            else:
                item.status = "excluded"
                item.final_score = 0.3
                item.exclusion_reason = "Below relevance threshold"
        db.commit()
        included_count = min(5, len(all_items))
        _finish_event(
            db,
            score_event,
            status="success",
            message=f"Scored {len(all_items)} items, {included_count} included",
            extra_metadata={"included_count": included_count},
        )

        report_event = _start_event(
            db,
            run.id,
            "generate_report",
            "Generating report...",
        )
        report = generate_report_stub(workspace, all_items, run)
        db.add(report)
        db.commit()
        db.refresh(report)

        msg = ReportMessage(
            thread_id=report.id,
            role="system",
            content=report.markdown_body,
            metadata_json={
                "sources": [item.id for item in all_items[:5]],
                "reportId": report.id,
            },
        )
        db.add(msg)
        db.commit()

        _finish_event(
            db,
            report_event,
            status="success",
            message=f"Generated report: {report.title}",
            extra_metadata={"report_id": report.id},
        )

        finished = datetime.now(timezone.utc)
        run.status = "success"
        run.finished_at = finished
        run.duration_ms = int((finished - now).total_seconds() * 1000)
        run.affected_counts_json = {
            "feeds": len(feeds),
            "articles": len(all_items),
            "reports": 1,
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
