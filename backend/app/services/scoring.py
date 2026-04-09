"""Pure utility functions for cheap relevance scoring of content items."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.content import ContentItem
from app.models.workspace import Workspace

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feedback adjustment constants
# ---------------------------------------------------------------------------

# Lightweight score adjustment applied per matching preference.
# The raw weight from the preference model (typically -1.0 to +3.0) is
# multiplied by this factor so that feedback never dominates the core score.
_FEEDBACK_ADJUSTMENT_FACTOR: float = 0.05

# Maximum absolute adjustment cap so no single signal can swing a score
# more than this amount.
_FEEDBACK_ADJUSTMENT_CAP: float = 0.15


# ---------------------------------------------------------------------------
# Keyword matching
# ---------------------------------------------------------------------------


def compute_keyword_score(text: str, keywords: list[str]) -> float:
    """Return a normalised 0.0–1.0 score based on keyword match ratio.

    The score is the fraction of *keywords* found (case-insensitive) in *text*.
    Returns 0.0 when either *text* or *keywords* is empty.
    """
    if not text or not keywords:
        return 0.0

    lower_text = text.lower()
    matched = sum(1 for kw in keywords if kw.lower() in lower_text)
    return matched / len(keywords)


# ---------------------------------------------------------------------------
# Competitor mention detection
# ---------------------------------------------------------------------------


def compute_competitor_mention_score(
    text: str,
    competitors: list[str],
) -> float:
    """Return 1.0 if any competitor name appears in *text*, else 0.0.

    Matching is case-insensitive and partial-word (substring).
    """
    if not text or not competitors:
        return 0.0

    lower_text = text.lower()
    for name in competitors:
        if name.lower() in lower_text:
            return 1.0
    return 0.0


# ---------------------------------------------------------------------------
# Excluded topic detection
# ---------------------------------------------------------------------------


def compute_excluded_topic_score(
    text: str,
    excluded_topics: list[str],
) -> float:
    """Return 1.0 if any excluded topic term appears in *text*, else 0.0.

    A score of 1.0 signals the content should be excluded.
    """
    if not text or not excluded_topics:
        return 0.0

    lower_text = text.lower()
    for topic in excluded_topics:
        if topic.lower() in lower_text:
            return 1.0
    return 0.0


# ---------------------------------------------------------------------------
# Freshness / recency
# ---------------------------------------------------------------------------


def compute_freshness_score(
    published_at: datetime | None,
    max_age_hours: float = 168.0,
) -> float:
    """Return a linear-decay freshness score between 0.0 and 1.0.

    * Just published  → 1.0
    * ``max_age_hours`` old  → 0.0
    * Older than ``max_age_hours``  → 0.0
    * ``published_at`` is ``None``  → 0.5 (neutral)
    """
    if published_at is None:
        return 0.5

    now = datetime.now(timezone.utc)

    # Ensure both datetimes are timezone-aware for correct arithmetic.
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    age_seconds = (now - published_at).total_seconds()
    max_age_seconds = max_age_hours * 3600.0

    if age_seconds <= 0:
        return 1.0
    if age_seconds >= max_age_seconds:
        return 0.0

    return 1.0 - (age_seconds / max_age_seconds)


# ---------------------------------------------------------------------------
# Source authority
# ---------------------------------------------------------------------------


def compute_source_authority_score(
    domain: str,
    trusted_domains: list[str] | None = None,
) -> float:
    """Return a source-authority score.

    * domain is in ``trusted_domains`` → 1.0
    * ``trusted_domains`` is empty or ``None`` → 0.5 (neutral)
    * otherwise → 0.3
    """
    if not domain:
        return 0.3

    if trusted_domains is None or len(trusted_domains) == 0:
        return 0.5

    lower_domain = domain.lower()
    lower_trusted = {d.lower() for d in trusted_domains}

    if lower_domain in lower_trusted:
        return 1.0

    return 0.3


# ---------------------------------------------------------------------------
# BM25-style scoring (simplified, per-document)
# ---------------------------------------------------------------------------


def compute_bm25_score(text: str, query_terms: list[str]) -> float:
    """Return a simplified BM25-style score based on term frequency.

    The text is tokenised by whitespace and lowercased.  For each *query_term*
    the raw term frequency (TF) in the text is computed.  The final score is
    the average of ``log(1 + tf)`` across all query terms (missing terms
    contribute 0), capped at 1.0.

    Returns 0.0 when *text* or *query_terms* is empty.
    """
    if not text or not query_terms:
        return 0.0

    tokens = text.lower().split()
    if not tokens:
        return 0.0

    # Build term frequencies
    tf: dict[str, int] = {}
    for token in tokens:
        tf[token] = tf.get(token, 0) + 1

    # Sum log(1 + tf) for each query term present
    raw_score = 0.0
    for term in query_terms:
        term_lower = term.lower()
        if term_lower in tf:
            raw_score += math.log(1 + tf[term_lower])

    # Normalise by number of query terms so the score reflects match density
    normalised = raw_score / len(query_terms)
    return min(normalised, 1.0)


# ---------------------------------------------------------------------------
# Combined scoring
# ---------------------------------------------------------------------------

# Default weights for the combined relevance score.
_WEIGHTS: dict[str, float] = {
    "keyword": 0.25,
    "competitor_mention": 0.20,
    "freshness": 0.20,
    "source_authority": 0.15,
    "bm25": 0.20,
}


def compute_combined_score(scores: dict) -> tuple[float, dict]:
    """Compute a weighted combined relevance score from individual scores.

    Parameters
    ----------
    scores:
        A dict that may contain any of the keys ``keyword``,
        ``competitor_mention``, ``freshness``, ``source_authority``, ``bm25``.
        Missing keys default to 0.0.

    Returns
    -------
    (combined_score, breakdown) where:
    - ``combined_score`` is the weighted sum.
    - ``breakdown`` is a JSON-serialisable dict containing the individual
      scores, the weights used, and the final combined score.
    """
    combined = 0.0
    breakdown: dict = {
        "weights": dict(_WEIGHTS),
        "scores": {},
    }

    for key, weight in _WEIGHTS.items():
        value = float(scores.get(key, 0.0))
        breakdown["scores"][key] = value
        combined += weight * value

    # Clamp to [0, 1]
    combined = max(0.0, min(1.0, combined))

    breakdown["combined_score"] = combined
    return combined, breakdown


# ---------------------------------------------------------------------------
# Pipeline-level scoring: score a batch of ContentItems against a workspace
# ---------------------------------------------------------------------------


def _extract_domain(url: str | None) -> str:
    """Extract the hostname from a URL string, returning empty string on failure."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        return parsed.hostname or ""
    except Exception:
        return ""


def _load_feedback_signals(
    db: Session, workspace_id: str
) -> tuple[dict[str, float], dict[str, float], int]:
    """Load feedback preferences and event count for a workspace.

    Returns
    -------
    (topic_weights, source_weights, feedback_event_count) where:
    - ``topic_weights`` maps lowercase topic → aggregated weight
    - ``source_weights`` maps lowercase source_name → aggregated weight
    - ``feedback_event_count`` is the total number of FeedbackEvent rows
    """
    topic_weights: dict[str, float] = {}
    source_weights: dict[str, float] = {}
    feedback_event_count: int = 0

    try:
        from app.models.preferences import TopicPreference, SourcePreference

        # Load topic preferences
        topic_prefs = (
            db.query(TopicPreference)
            .filter(TopicPreference.workspace_id == workspace_id)
            .all()
        )
        for tp in topic_prefs:
            key = tp.topic.lower()
            topic_weights[key] = topic_weights.get(key, 0.0) + tp.weight

        # Load source preferences
        source_prefs = (
            db.query(SourcePreference)
            .filter(SourcePreference.workspace_id == workspace_id)
            .all()
        )
        for sp in source_prefs:
            key = sp.source_name.lower()
            source_weights[key] = source_weights.get(key, 0.0) + sp.weight

    except Exception:
        # Gracefully handle missing table / model — log and continue.
        logger.debug(
            "Could not load preference models for feedback scoring", exc_info=True
        )

    try:
        from app.models.report import FeedbackEvent

        feedback_event_count = (
            db.query(FeedbackEvent)
            .filter(FeedbackEvent.workspace_id == workspace_id)
            .count()
        )
    except Exception:
        logger.debug("Could not load feedback event count", exc_info=True)

    return topic_weights, source_weights, feedback_event_count


def _compute_feedback_adjustment(
    item_text: str,
    source_name: str | None,
    topic_weights: dict[str, float],
    source_weights: dict[str, float],
) -> tuple[float, list[str], list[str]]:
    """Compute a lightweight score adjustment from feedback preferences.

    Returns
    -------
    (adjustment, topics_matched, sources_matched) where:
    - ``adjustment`` is the net score delta (clamped to ±_FEEDBACK_ADJUSTMENT_CAP)
    - ``topics_matched`` lists the lowercase topic keys that matched
    - ``sources_matched`` lists the lowercase source keys that matched
    """
    adjustment = 0.0
    topics_matched: list[str] = []
    sources_matched: list[str] = []

    lower_text = item_text.lower()

    # Topic preference adjustments
    for topic_key, weight in topic_weights.items():
        if topic_key in lower_text:
            delta = weight * _FEEDBACK_ADJUSTMENT_FACTOR
            # Clamp individual delta
            delta = max(-_FEEDBACK_ADJUSTMENT_CAP, min(_FEEDBACK_ADJUSTMENT_CAP, delta))
            adjustment += delta
            topics_matched.append(topic_key)

    # Source preference adjustments
    if source_name:
        lower_source = source_name.lower()
        for src_key, weight in source_weights.items():
            if lower_source == src_key or src_key in lower_source:
                delta = weight * _FEEDBACK_ADJUSTMENT_FACTOR
                delta = max(
                    -_FEEDBACK_ADJUSTMENT_CAP, min(_FEEDBACK_ADJUSTMENT_CAP, delta)
                )
                adjustment += delta
                sources_matched.append(src_key)

    # Clamp total adjustment
    adjustment = max(
        -_FEEDBACK_ADJUSTMENT_CAP, min(_FEEDBACK_ADJUSTMENT_CAP, adjustment)
    )

    return adjustment, topics_matched, sources_matched


def score_content_items(
    db: Session,
    items: list[ContentItem],
    workspace: Workspace,
) -> dict:
    """Score a list of ContentItems using workspace profile/settings.

    For each item the function:
    1. Computes individual scores (keyword, competitor, freshness, source, bm25).
    2. Combines them into a weighted score via ``compute_combined_score``.
    3. Checks excluded topics and the minimum relevance threshold.
    4. Persists the results on the ORM objects and commits.

    Parameters
    ----------
    db:
        SQLAlchemy session (used to flush/persist changes).
    items:
        ContentItem ORM objects to score.
    workspace:
        The workspace whose profile/settings define scoring context.

    Returns
    -------
    A dict with summary metadata::

        {
            "included_count": int,
            "excluded_count": int,
            "avg_score": float,
            "min_score": float,
            "max_score": float,
        }
    """
    # ------------------------------------------------------------------
    # 1. Load workspace context (gracefully handle missing profile/settings)
    # ------------------------------------------------------------------
    profile = workspace.profile
    settings = workspace.settings

    priority_themes: list[str] = (
        list(profile.priority_themes) if profile and profile.priority_themes else []
    )
    competitors: list[str] = (
        list(profile.competitors) if profile and profile.competitors else []
    )
    excluded_topics: list[str] = (
        list(profile.excluded_topics) if profile and profile.excluded_topics else []
    )

    # trusted_domains may live inside settings.thresholds or be absent
    trusted_domains: list[str] | None = None
    if settings and settings.thresholds:
        trusted_domains = settings.thresholds.get("trusted_domains")
        if trusted_domains is not None:
            trusted_domains = list(trusted_domains)

    # Minimum relevance threshold (default 0.1)
    min_relevance_score: float = 0.1
    if settings and settings.thresholds:
        min_relevance_score = float(settings.thresholds.get("min_relevance_score", 0.1))

    # ------------------------------------------------------------------
    # 1b. Load feedback signals for the workspace
    # ------------------------------------------------------------------
    topic_weights, source_weights, feedback_event_count = _load_feedback_signals(
        db, workspace.id
    )

    # ------------------------------------------------------------------
    # 2. Score each item
    # ------------------------------------------------------------------
    included_count = 0
    excluded_count = 0
    scores_list: list[float] = []

    for item in items:
        # Build the text blob to score: title + summary (with raw_text as fallback)
        parts: list[str] = []
        if item.title:
            parts.append(item.title)
        if item.summary_snippet:
            parts.append(item.summary_snippet)
        elif item.raw_text:
            # Use first 1000 chars of raw_text as a fallback summary
            parts.append(item.raw_text[:1000])
        item_text = " ".join(parts)

        # Compute individual scores
        individual_scores: dict[str, float] = {
            "keyword": compute_keyword_score(item_text, priority_themes),
            "competitor_mention": compute_competitor_mention_score(
                item_text, competitors
            ),
            "freshness": compute_freshness_score(
                item.published_at  # type: ignore[arg-type]
                if not isinstance(item.published_at, str)
                else None,
            ),
            "source_authority": compute_source_authority_score(
                _extract_domain(item.url),
                trusted_domains,
            ),
            "bm25": compute_bm25_score(item_text, priority_themes),
        }

        # Combined weighted score
        combined_score, breakdown = compute_combined_score(individual_scores)

        # Check excluded topics
        excluded_score = compute_excluded_topic_score(item_text, excluded_topics)
        breakdown["excluded_topic_score"] = excluded_score

        # ------------------------------------------------------------------
        # 2b. Apply feedback adjustment
        # ------------------------------------------------------------------
        feedback_adj, topics_matched, sources_matched = _compute_feedback_adjustment(
            item_text, item.source_name, topic_weights, source_weights
        )
        if feedback_adj != 0.0:
            combined_score = max(0.0, min(1.0, combined_score + feedback_adj))
            breakdown["feedback_adjustment"] = feedback_adj

        feedback_info: dict = {}
        if topics_matched:
            feedback_info["topics_matched"] = topics_matched
        if sources_matched:
            feedback_info["sources_matched"] = sources_matched
        if feedback_info:
            feedback_info["event_count"] = feedback_event_count
            breakdown["feedback"] = feedback_info

        # ------------------------------------------------------------------
        # 3. Apply filtering rules
        # ------------------------------------------------------------------
        if excluded_score > 0:
            item.status = "excluded"
            item.exclusion_reason = "matched_excluded_topic"
            item.inclusion_reason = None
            breakdown["filter_reason"] = "matched_excluded_topic"
            excluded_count += 1
        elif combined_score < min_relevance_score:
            item.status = "excluded"
            item.exclusion_reason = "below_relevance_threshold"
            item.inclusion_reason = None
            breakdown["filter_reason"] = "below_relevance_threshold"
            breakdown["min_relevance_threshold"] = min_relevance_score
            excluded_count += 1
        else:
            item.status = "included"
            item.exclusion_reason = None
            item.inclusion_reason = f"combined_score={combined_score:.4f}"
            breakdown["filter_reason"] = "included"
            included_count += 1

        # ------------------------------------------------------------------
        # 4. Persist results on the item
        # ------------------------------------------------------------------
        item.score_breakdown_json = breakdown
        item.final_score = combined_score

        scores_list.append(combined_score)

    # Flush changes to the database
    db.flush()

    # ------------------------------------------------------------------
    # 5. Return summary metadata
    # ------------------------------------------------------------------
    if scores_list:
        avg_score = sum(scores_list) / len(scores_list)
        min_score = min(scores_list)
        max_score = max(scores_list)
    else:
        avg_score = 0.0
        min_score = 0.0
        max_score = 0.0

    return {
        "included_count": included_count,
        "excluded_count": excluded_count,
        "avg_score": avg_score,
        "min_score": min_score,
        "max_score": max_score,
    }
