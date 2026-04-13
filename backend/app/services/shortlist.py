"""Shortlist selection module.

Chooses the final candidate set for report generation by filtering,
deduplicating clusters, scoring, capping, and refining via LLM.

OpenCode is a mandatory dependency: every call to ``select_shortlist``
must provide a working ``OpenCodeClient``.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.content import ContentItem
from app.models.run import ProcessingRun, ProcessingRunEvent
from app.models.workspace import Workspace
from app.services.opencode_client import OpenCodeClient

logger = logging.getLogger(__name__)

# Default cap on the number of articles per report
_DEFAULT_MAX_ARTICLES = 15


def _require_opencode_client(opencode_client: OpenCodeClient | None) -> OpenCodeClient:
    """Return a validated OpenCode client or fail with a clear error."""
    if opencode_client is None:
        raise ValueError(
            "OpenCodeClient is required for shortlist refinement; received None"
        )
    return opencode_client


def select_shortlist(
    db: Session,
    items: list[ContentItem],
    workspace: Workspace,
    run: ProcessingRun,
    *,
    opencode_client: OpenCodeClient | None,
) -> list[ContentItem]:
    """Select the final shortlist of content items for report generation.

    Steps:
    1. Filter to items with status="included".
    2. Deduplicate by cluster (keep lead or highest-scored per cluster).
    3. Sort by final_score descending.
    4. Cap at workspace maxArticlesPerReport (default 15).
    5. Refine via LLM through the required *opencode_client*.

    Parameters
    ----------
    db:
        SQLAlchemy session.
    items:
        ContentItem ORM objects to select from.
    workspace:
        The workspace (provides settings/thresholds).
    run:
        The current processing run (available for future metadata storage).
    opencode_client:
        **Required** LLM client for shortlist refinement.  A missing
        client is a programmer/configuration error.

    Returns
    -------
    List of ContentItem objects in the final shortlist.

    Raises
    ------
    OpenCodeUnavailableError, OpenCodeTimeoutError, OpenCodeResponseError:
        If the LLM call fails.  These propagate to the caller; there is
        **no** silent fallback.
    """
    opencode_client = _require_opencode_client(opencode_client)

    # ------------------------------------------------------------------
    # 1. Filter to included items only
    # ------------------------------------------------------------------
    included = [item for item in items if item.status == "included"]

    # ------------------------------------------------------------------
    # 2. Cluster deduplication
    # ------------------------------------------------------------------
    deduped = _dedup_clusters(included)

    # ------------------------------------------------------------------
    # 3. Sort by final_score descending
    # ------------------------------------------------------------------
    deduped.sort(key=lambda item: item.final_score or 0.0, reverse=True)

    # ------------------------------------------------------------------
    # 4. Cap shortlist size
    # ------------------------------------------------------------------
    max_articles = _get_max_articles(workspace)
    capped = deduped[:max_articles]

    # ------------------------------------------------------------------
    # 5. Mandatory LLM refinement (explicit rerank stage)
    # ------------------------------------------------------------------
    if capped:
        capped = _rerank_via_llm(db, opencode_client, capped, workspace, run)

    return capped


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_max_articles(workspace: Workspace) -> int:
    """Return the max articles per report from workspace settings."""
    settings = workspace.settings
    if settings and settings.thresholds:
        return int(
            settings.thresholds.get("maxArticlesPerReport", _DEFAULT_MAX_ARTICLES)
        )
    return _DEFAULT_MAX_ARTICLES


def _dedup_clusters(items: list[ContentItem]) -> list[ContentItem]:
    """Deduplicate items by cluster, keeping the lead or highest-scored item.

    Items with ``cluster_id is None`` (unclustered) are all kept
    individually — they are not duplicates of one another.
    """
    clusters: dict[str | None, list[ContentItem]] = defaultdict(list)
    for item in items:
        clusters[item.cluster_id].append(item)

    result: list[ContentItem] = []
    for cluster_id, cluster_items in clusters.items():
        if cluster_id is None:
            # Unclustered items are all kept individually
            result.extend(cluster_items)
            continue

        # Prefer the designated lead item
        leads = [item for item in cluster_items if item.is_lead]
        if leads:
            result.append(leads[0])
        else:
            # Fall back to the highest-scored item in the cluster
            best = max(cluster_items, key=lambda i: i.final_score or 0.0)
            result.append(best)

    return result


def _persist_rerank_event(
    db: Session,
    run: ProcessingRun,
    *,
    stage: str,
    items_data: list[dict[str, Any]],
    message: str,
) -> ProcessingRunEvent:
    """Create a pipeline run event for the rerank stage."""
    now = datetime.now(timezone.utc)
    event = ProcessingRunEvent(
        run_id=run.id,
        step_name=stage,
        status="completed",
        message=message,
        metadata_json={
            "stage": stage,
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "items": items_data,
        },
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    logger.info("Persisted rerank event stage=%s item_count=%d", stage, len(items_data))
    return event


def _rerank_via_llm(
    db: Session,
    client: OpenCodeClient,
    items: list[ContentItem],
    workspace: Workspace,
    run: ProcessingRun,
) -> list[ContentItem]:
    """Explicit rerank stage: score-based candidates → LLM-refined shortlist.

    This function:
    1. Persists the pre-rerank candidate set as a run event.
    2. Calls the LLM to rerank/filter candidates.
    3. Persists the post-rerank shortlist as a run event.

    **Exceptions from the LLM call are not caught** — they propagate to the
    caller so the pipeline can mark the run as failed.
    """
    # ------------------------------------------------------------------
    # 1. Persist pre-rerank candidate set
    # ------------------------------------------------------------------
    pre_rerank_data: list[dict[str, Any]] = []
    for item in items:
        pre_rerank_data.append(
            {
                "id": item.id,
                "title": item.title,
                "score": item.final_score,
                "source_type": item.content_type,
                "source_name": item.source_name,
            }
        )
    _persist_rerank_event(
        db,
        run,
        stage="pre_rerank",
        items_data=pre_rerank_data,
        message=f"Pre-rerank candidate set: {len(items)} items",
    )

    # ------------------------------------------------------------------
    # 2. Build lightweight dicts for the LLM
    # ------------------------------------------------------------------
    item_dicts: list[dict[str, Any]] = []
    for item in items:
        item_dicts.append(
            {
                "id": item.id,
                "title": item.title,
                "url": item.url,
                "summary": item.summary_snippet,
                "source_name": item.source_name,
                "source_type": item.content_type,
                "score": item.final_score,
                "published_at": (
                    item.published_at.isoformat() if item.published_at else None
                ),
            }
        )

    # Build workspace context
    workspace_context: dict[str, Any] = {
        "workspace_id": workspace.id,
        "name": workspace.name,
        "customer": workspace.customer,
    }
    if workspace.profile:
        workspace_context["priority_themes"] = workspace.profile.priority_themes or []
        workspace_context["competitors"] = workspace.profile.competitors or []
        workspace_context["excluded_topics"] = workspace.profile.excluded_topics or []

    # ------------------------------------------------------------------
    # 3. Call the LLM — exceptions propagate (no silent fallback)
    # ------------------------------------------------------------------
    llm_result = client.refine_shortlist(item_dicts, workspace_context)

    # Log the rationale
    if llm_result.rationale:
        logger.info("LLM rerank rationale: %s", llm_result.rationale)

    # ------------------------------------------------------------------
    # 4. Match LLM-selected items back to ContentItem objects by id
    # ------------------------------------------------------------------
    item_by_id: dict[str, ContentItem] = {item.id: item for item in items}
    refined: list[ContentItem] = []
    # Build a map of LLM reasons per selected item
    llm_reasons: dict[str, str] = {}
    for selected in llm_result.selected_items:
        item_id = selected.get("id")
        reason = selected.get("reason", "")
        if item_id and item_id in item_by_id:
            refined.append(item_by_id[item_id])
        if item_id and reason:
            llm_reasons[item_id] = reason

    # Validate: identify any IDs the LLM returned that don't match known items
    requested_ids = {s.get("id") for s in llm_result.selected_items if s.get("id")}
    resolved_ids = {item.id for item in refined}
    unresolved_ids = requested_ids - resolved_ids
    for uid in unresolved_ids:
        logger.warning("LLM rerank: unresolved ID %s", uid)
    logger.info(
        "LLM rerank: %d candidates, %d selected, %d unresolved",
        len(items),
        len(resolved_ids),
        len(unresolved_ids),
    )

    # If the LLM returned no matching items, fall back to the score-based
    # shortlist.  This is a response-validation safeguard for cases where
    # the LLM returns IDs that cannot be resolved to known items — it is
    # NOT a disabled-mode fallback.  The LLM call itself always runs.
    if not refined:
        logger.warning(
            "LLM rerank returned no matching items; "
            "using score-based shortlist as response-validation safeguard"
        )
        refined = items

    # ------------------------------------------------------------------
    # 5. Persist post-rerank shortlist
    # ------------------------------------------------------------------
    post_rerank_data: list[dict[str, Any]] = []
    for item in refined:
        post_rerank_data.append(
            {
                "id": item.id,
                "title": item.title,
                "score": item.final_score,
                "source_type": item.content_type,
                "source_name": item.source_name,
                "reason": llm_reasons.get(item.id, ""),
            }
        )
    _persist_rerank_event(
        db,
        run,
        stage="post_rerank",
        items_data=post_rerank_data,
        message=(
            f"Post-rerank shortlist: {len(refined)} items selected "
            f"from {len(items)} candidates"
        ),
    )

    return refined
