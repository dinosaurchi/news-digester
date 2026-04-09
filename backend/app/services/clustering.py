"""Clustering/dedup pipeline step — groups content items into clusters.

Uses the dedup utility functions to identify near-duplicate articles and
group them under a shared :class:`ContentCluster` record.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.content import ContentCluster, ContentItem
from app.services.dedup import (
    compute_similarity,
    normalize_url,
    title_fingerprint,
    token_overlap_similarity,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

# Default threshold for the weighted combined similarity score.
DEFAULT_SIMILARITY_THRESHOLD: float = 0.7

# Default threshold for same-domain title-only similarity.
DEFAULT_DOMAIN_TITLE_THRESHOLD: float = 0.6


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _item_to_dict(item: ContentItem) -> dict[str, Any]:
    """Convert a ContentItem to the dict shape expected by ``compute_similarity``."""
    return {
        "url": item.url,
        "title": item.title,
        "published_at": item.published_at,
    }


def _is_better_lead(candidate: ContentItem, current: ContentItem) -> bool:
    """Return ``True`` when *candidate* should replace *current* as lead.

    Priority:
    1. Item with a ``published_at`` wins over one without.
    2. Among items with ``published_at``, the earliest wins.
    3. Among items without ``published_at``, the highest score wins
       (``final_score`` then ``local_relevance_score``).
    4. Tiebreaker: earliest ``created_at``.
    """
    cand_pub: datetime | None = candidate.published_at
    curr_pub: datetime | None = current.published_at

    # (1) Has published_at beats missing published_at
    if cand_pub is not None and curr_pub is None:
        return True
    if curr_pub is not None and cand_pub is None:
        return False

    # (2) Both have published_at — earlier wins
    if cand_pub is not None and curr_pub is not None:
        if cand_pub != curr_pub:
            return cand_pub < curr_pub

    # (3) Neither has published_at — compare scores
    cand_score = candidate.final_score or candidate.local_relevance_score or 0.0
    curr_score = current.final_score or current.local_relevance_score or 0.0
    if cand_score != curr_score:
        return cand_score > curr_score

    # (4) Tiebreaker — earliest created_at wins
    cand_created: datetime | None = candidate.created_at
    curr_created: datetime | None = current.created_at
    if cand_created and curr_created:
        return cand_created < curr_created

    return False


def _select_lead_item(items: list[ContentItem]) -> ContentItem:
    """Pick the best lead item from a cluster of items."""
    best = items[0]
    for item in items[1:]:
        if _is_better_lead(item, best):
            best = item
    return best


def _has_is_lead_field(item: ContentItem) -> bool:
    """Check whether the ORM mapper exposes an ``is_lead`` attribute.

    The column will be added in a later pass (7.2.4); until then we skip
    setting it so the pipeline works on both old and new schemas.
    """
    return hasattr(item, "is_lead")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def cluster_content_items(
    db: Session,
    items: list[ContentItem],
    workspace_id: str,
    *,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    domain_title_threshold: float = DEFAULT_DOMAIN_TITLE_THRESHOLD,
) -> dict[str, int]:
    """Group *items* into :class:`ContentCluster` records.

    Phases
    ~~~~~~

    1. **URL exact match** — items sharing a normalised URL.
    2. **Title fingerprint** — items sharing a normalised-title SHA-256 hash.
    3. **Similarity** — greedy pairwise comparison via
       :func:`~app.services.dedup.compute_similarity`.
    4. **Singletons** — every remaining item gets its own cluster.

    Parameters
    ----------
    db:
        Active SQLAlchemy session (will be committed).
    items:
        ContentItem records to cluster.  They **must** already be persisted
        (have an ``id``).
    workspace_id:
        Owning workspace — set on every created cluster.
    similarity_threshold:
        Minimum ``combined_score`` for two items to be clustered in Phase 3.
    domain_title_threshold:
        Minimum token-overlap title similarity when items share the same
        domain (Phase 3 secondary rule).

    Returns
    -------
    dict
        ``clusters_created``, ``items_clustered``, ``singleton_clusters``.
    """
    if not items:
        return {
            "clusters_created": 0,
            "items_clustered": 0,
            "singleton_clusters": 0,
        }

    # ``clustered`` tracks item IDs already assigned to a cluster.
    clustered: set[str] = set()
    # Ordered groups: key → list of ContentItem (at least 2 members each).
    groups: list[tuple[str, list[ContentItem]]] = []

    # ── Phase 1: URL exact match grouping ────────────────────────────────
    url_buckets: dict[str, list[ContentItem]] = defaultdict(list)
    for item in items:
        norm = normalize_url(item.url)
        if norm:
            url_buckets[norm].append(item)

    phase1_count = 0
    for _norm, bucket in url_buckets.items():
        if len(bucket) < 2:
            continue
        groups.append((f"url:{bucket[0].id}", bucket))
        for item in bucket:
            clustered.add(item.id)
        phase1_count += 1

    logger.info(
        "Phase 1 (URL exact): %d groups, %d items",
        phase1_count,
        sum(len(g[1]) for g in groups),
    )

    # ── Phase 2: Title fingerprint grouping ──────────────────────────────
    title_buckets: dict[str, list[ContentItem]] = defaultdict(list)
    for item in items:
        if item.id in clustered:
            continue
        fp = title_fingerprint(item.title)
        if fp:
            title_buckets[fp].append(item)

    phase2_count = 0
    for _fp, bucket in title_buckets.items():
        if len(bucket) < 2:
            continue
        groups.append((f"title:{bucket[0].id}", bucket))
        for item in bucket:
            clustered.add(item.id)
        phase2_count += 1

    logger.info(
        "Phase 2 (Title fingerprint): %d groups, %d new items",
        phase2_count,
        sum(len(g[1]) for g in groups) - sum(len(g[1]) for g in groups[:phase1_count]),
    )

    # ── Phase 3: Similarity-based grouping ───────────────────────────────
    remaining = [item for item in items if item.id not in clustered]
    sim_cluster_idx = 0

    for i, item_a in enumerate(remaining):
        if item_a.id in clustered:
            continue

        for j in range(i + 1, len(remaining)):
            item_b = remaining[j]
            if item_b.id in clustered:
                continue

            sim = compute_similarity(_item_to_dict(item_a), _item_to_dict(item_b))

            should_cluster = False

            # Primary: combined weighted score exceeds threshold
            if sim["combined_score"] >= similarity_threshold:
                should_cluster = True

            # Secondary: same domain + high title overlap
            if not should_cluster and sim["domain_match"]:
                title_sim = token_overlap_similarity(
                    item_a.title or "", item_b.title or ""
                )
                if title_sim > domain_title_threshold:
                    should_cluster = True

            if should_cluster:
                key = f"sim:{sim_cluster_idx}"
                groups.append((key, [item_a, item_b]))
                clustered.add(item_a.id)
                clustered.add(item_b.id)
                sim_cluster_idx += 1
                break  # greedy — move on to the next seed item

        # If no match was found, item_a stays unclustered for Phase 4.

    phase3_items = sum(len(g[1]) for g in groups if g[0].startswith("sim:"))
    logger.info(
        "Phase 3 (Similarity): %d groups, %d new items",
        sim_cluster_idx,
        phase3_items,
    )

    # ── Phase 4: Singleton clusters ──────────────────────────────────────
    singleton_count = 0
    for item in items:
        if item.id not in clustered:
            groups.append((f"singleton:{item.id}", [item]))
            clustered.add(item.id)
            singleton_count += 1

    logger.info("Phase 4 (Singletons): %d items", singleton_count)

    # ── Lead selection & persistence ─────────────────────────────────────
    total_clusters = 0
    total_items = 0
    total_singletons = 0

    for _key, group_items in groups:
        lead = _select_lead_item(group_items)

        cluster = ContentCluster(
            workspace_id=workspace_id,
            label=(lead.title or "")[:500],
            item_count=len(group_items),
        )
        db.add(cluster)
        db.flush()  # populate cluster.id

        for item in group_items:
            item.cluster_id = cluster.id
            if _has_is_lead_field(item):
                item.is_lead = item.id == lead.id  # type: ignore[attr-defined]

        total_items += len(group_items)
        if len(group_items) == 1:
            total_singletons += 1
        total_clusters += 1

    db.commit()

    logger.info(
        "Clustering complete: %d clusters (%d singletons), %d items assigned",
        total_clusters,
        total_singletons,
        total_items,
    )

    return {
        "clusters_created": total_clusters,
        "items_clustered": total_items,
        "singleton_clusters": total_singletons,
    }
